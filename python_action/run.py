"""Run clang-tidy and clang-format on a list of changed files provided by GitHub's
REST API. If executed from command-line, then [`main()`][python_action.run.main] is
the entrypoint.

!!! info "See Also"
    - [github rest API reference for pulls](https://docs.github.com/en/rest/reference/pulls)
    - [github rest API reference for repos](https://docs.github.com/en/rest/reference/repos)
    - [github rest API reference for issues](https://docs.github.com/en/rest/reference/issues)
"""
import subprocess
import os
import sys
import re
import argparse
import json
import requests
from . import Globals, GlobalParser, logger, GITHUB_TOKEN, API_HEADERS
from .clang_tidy_yml import parse_tidy_suggestions_yml as parse_tidy_advice
from .clang_tidy import parse_tidy_output
from .clang_format_xml import parse_format_replacements_xml as parse_fmt_advice
from .thread_comments import remove_bot_comments, get_review_id, list_diff_comments


# global constant variables
GITHUB_EVEN_PATH = os.getenv("GITHUB_EVENT_PATH", "event_payload.json")
GITHUB_API_URL = os.getenv("GITHUB_API_URL", "https://api.github.com")
GITHUB_REPOSITORY = os.getenv("GITHUB_REPOSITORY", "2bndy5/cpp-linter-action")
GITHUB_SHA = os.getenv("GITHUB_SHA", "293af27ec15d6094a5308fe655a7e111e5b8721a")
GITHUB_EVENT_NAME = os.getenv("GITHUB_EVENT_NAME", "pull_request")

# setup CLI args
cli_arg_parser = argparse.ArgumentParser(
    description=__doc__[: __doc__.find("If executed from")]
)
cli_arg_parser.add_argument(
    "--verbosity",
    default="10",
    help="The logging level. Defaults to level 20 (aka 'logging.INFO').",
)
cli_arg_parser.add_argument(
    "--style",
    default="llvm",
    help="The style rules to use (defaults to 'llvm'). Set this to 'file' to have "
    "clang-format use the closest relative .clang-format file.",
)
cli_arg_parser.add_argument(
    "--extensions",
    default="c,h,C,H,cpp,hpp,cc,hh,c++,h++,cxx,hxx",
    help="The file extensions to run the action against. This comma-separated string "
    "defaults to 'c,h,C,H,cpp,hpp,cc,hh,c++,h++,cxx,hxx'.",
)
cli_arg_parser.add_argument(
    "--tidy-checks",
    default="boost-*,bugprone-*,performance-*,readability-*,portability-*,modernize-*,"
    "clang-analyzer-*,cppcoreguidelines-*",
    help="A string of regex-like patterns specifying what checks clang-tidy will use. "
    "This defaults to 'boost-*,bugprone-*,performance-*,readability-*,portability-*,"
    "modernize-*,clang-analyzer-*,cppcoreguidelines-*'. See also clang-tidy docs for "
    "more info.",
)
cli_arg_parser.add_argument(
    "--repo-root",
    default=".",
    help="The relative path to the repository root directory. The default value '.' is "
    "relative to the runner's GITHUB_WORKSPACE environment variable.",
)
cli_arg_parser.add_argument(
    "--version",
    default="10",
    help="The desired version of the clang tools to use. Accepted options are strings "
    "which can be 6.0, 7, 8, 9, 10, 11, 12. Defaults to 10.",
)
cli_arg_parser.add_argument(
    "--diff-only",
    default="false",
    type=lambda input: input.lower() == "true",
    help="Set this option to 'true' to only analyse changes in the event's diff. "
    "Defaults to 'false'.",
)


def set_exit_code(override: int = None):
    """Set the action's exit code.

    Args:
        override: The number to use when overriding the action's logic."""
    exit_code = override if override is not None else bool(Globals.OUTPUT)
    print(f"::set-output name=checks-failed::{exit_code}")
    return exit_code


def get_list_of_changed_files():
    """Fetch the JSON payload of the event's changed files. Sets the
    [`FILES`][python_action.__init__.Globals.FILES] attribute."""
    logger.info(f"processing {GITHUB_EVENT_NAME} event")
    with open(GITHUB_EVEN_PATH, "r", encoding="utf-8") as payload:
        Globals.EVENT_PAYLOAD = json.load(payload)
        logger.debug(json.dumps(Globals.EVENT_PAYLOAD))

    files_link = f"{GITHUB_API_URL}/repos/{GITHUB_REPOSITORY}/"
    if GITHUB_EVENT_NAME == "pull_request":
        files_link += f"pulls/{Globals.EVENT_PAYLOAD['number']}/files"

    elif GITHUB_EVENT_NAME == "push":
        files_link += f"commits/{GITHUB_SHA}"
    else:
        logger.warn("triggered on unsupported event.")
        sys.exit(set_exit_code(0))
    logger.info(f"Fetching files list from url: {files_link}")
    Globals.FILES = requests.get(files_link).json()
    # logger.debug("files json:\n" + json.dumps(Globals.FILES, indent=2))


def filter_out_non_source_files(ext_list: str, diff_only: bool):
    """Exclude undesired files (specified by user input 'extensions'). This filter
    applies to the event's [`FILES`][python_action.__init__.Globals.FILES] attribute.

    Args:
        ext_list: A comma-separated `str` of extensions that are concerned.
        diff_only: A flag that forces focus on only changes in the event's diff info.

    !!! note
        This will exit early when nothing left to do.
    """
    ext_list = ext_list.split(",")
    files = []
    for file in (
        Globals.FILES if GITHUB_EVENT_NAME == "pull_request" else Globals.FILES["files"]
    ):
        extension = re.search("\.\w+$", file["filename"])
        if (
            extension is not None
            and extension.group(0)[1:] in ext_list
            and not file["status"].endswith("removed")
        ):
            if diff_only and "patch" not in file.keys():
                continue
            files.append(file)

    if not files:
        # exit early if no changed files are source files
        logger.info("No source files need checking!")
        sys.exit(set_exit_code(0))
    else:
        if GITHUB_EVENT_NAME == "pull_request":
            Globals.FILES = files
        else:
            Globals.FILES["files"] = files
        with open(
            ".cpp_linter_action_changed_files.json", "w", encoding="utf-8"
        ) as temp:
            json.dump(Globals.FILES, temp)
    logger.info("File names:\n\t{}".format("\n\t".join([f["filename"] for f in files])))


def verify_files_are_present():
    """Download the files if not present.

    !!! hint
        This function assumes the working directory is the root of the invoking
        repository. If files are not found, then they are downloaded to the working
        directory. This may be bad for files with the same name from different folders.
    """
    for file in (
        Globals.FILES if GITHUB_EVENT_NAME == "pull_request" else Globals.FILES["files"]
    ):
        file_name = file["filename"].replace("/", os.sep)
        if not os.path.exists(file_name):
            logger.info(f'Downloading file from url: {file["raw_url"]}')
            download = requests.get(file["raw_url"])
            with open(os.path.split(file_name)[1], "w", encoding="utf-8") as temp:
                temp.write(download)


def capture_clang_tools_output(version: str, checks: str, style: str, diff_only: bool):
    """Execute and capture all output from clang-tidy and clang-format. This aggregates
    results in the [`OUTPUT`][python_action.__init__.Globals.OUTPUT].

    Args:
        version: The version of clang-tidy to run.
        checks: The `str` of comma-separated regulate expressions that describe
            the desired clang-tidy checks to be enabled/configured.
        style: The clang-format style rules to adhere. Set this to 'file' to
            use the relative-most .clang-format configuration file.
        diff_only: A flag that forces focus on only changes in the event's diff info.
    """
    for index, file in enumerate(
        Globals.FILES if GITHUB_EVENT_NAME == "pull_request" else Globals.FILES["files"]
    ):
        filename = file["filename"]
        if not os.path.exists(file["filename"]):
            filename = os.path.split(file["raw_url"])[1]
        logger.info(f"Performing checkup on {filename}")

        if diff_only:
            # get diff details for the file's changes
            line_filter = {"name": filename.replace("/", os.sep), "lines": []}
            diff_line_map, line_numb_in_diff = ({}, 0)
            # diff_line_map is a dict for which each
            #     - key is the line number in the file
            #     - value is the line's "position" in the diff
            for i, line in enumerate(file["patch"].splitlines()):
                if line.startswith("@@ -"):
                    changed_hunk = line[line.find(" +") + 2 : line.find(" @@")]
                    changed_hunk = changed_hunk.split(",")
                    start_line = int(changed_hunk[0])
                    hunk_length = int(changed_hunk[1])
                    line_filter["lines"].append([start_line, hunk_length + start_line])
                    line_numb_in_diff = start_line
                elif not line.startswith("-"):
                    diff_line_map[line_numb_in_diff] = i
                    line_filter["lines"][-1][1] = line_numb_in_diff
                    line_numb_in_diff += 1
            Globals.FILES[index]["diff_line_map"] = diff_line_map
            logger.info("line_filter = " + json.dumps(line_filter["lines"]))

        # run clang-tidy
        cmds = [f"clang-tidy-{version}"]
        if sys.platform.startswith("win32"):
            cmds = ["clang-tidy"]
        if checks:
            cmds.append(f"-checks={checks}")
        cmds.append("--export-fixes=clang_tidy_output.yml")
        if diff_only:
            cmds.append(f"--line-filter={json.dumps([line_filter])}")
        cmds.append(filename.replace("/", os.sep))
        with open("clang_tidy_output.yml", "w", encoding="utf-8"):
            pass  # clear yml file's content before running clang-tidy
        with open("clang_tidy_report.txt", "w", encoding="utf-8") as f_out:
            subprocess.run(cmds, stdout=f_out)
        if os.path.getsize("clang_tidy_output.yml"):
            parse_tidy_advice()  # get clang-tidy fixes from yml

        # run clang-format
        cmds = [
            "clang-format"
            + ("" if sys.platform.startswith("win32") else f"-{version}"),
            f"-style={style}",
            "--output-replacements-xml",
        ]
        if diff_only:
            for line_range in line_filter["lines"]:
                cmds.append(f"--lines={line_range[0]}:{line_range[1]}")
        cmds.append(filename.replace("/", os.sep))

        with open("clang_format_output.xml", "w", encoding="utf-8") as f_out:
            subprocess.run(cmds, stderr=f_out, stdout=f_out)

        if os.path.getsize("clang_tidy_report.txt") and not diff_only:
            parse_tidy_output()  # get clang-tidy fixes from stdout
            if Globals.PAYLOAD_TIDY:
                Globals.PAYLOAD_TIDY += "<hr></details>"
            Globals.PAYLOAD_TIDY += f"<details><summary>{filename}</summary><br>\n"
            for fix in GlobalParser.tidy_notes:
                Globals.PAYLOAD_TIDY += repr(fix)
            GlobalParser.tidy_notes.clear()
            Globals.PAYLOAD_TIDY += "</details>"

        if os.path.getsize("clang_format_output.xml"):
            parse_fmt_advice(filename.replace("/", os.sep))  # parse clang-format fixes
            if not diff_only:
                if not Globals.OUTPUT:
                    Globals.OUTPUT = "<!-- cpp linter action -->\n## :scroll: "
                    Globals.OUTPUT += "Run `clang-format` on the following files\n"
                Globals.OUTPUT += f"- [ ] {file['filename']}\n"

    if Globals.PAYLOAD_TIDY:
        if not Globals.OUTPUT:
            Globals.OUTPUT = "<!-- cpp linter action -->\n"
        else:
            Globals.OUTPUT += "\n---\n"
        Globals.OUTPUT += "## :speech_balloon: Output from `clang-tidy`\n"
        Globals.OUTPUT += Globals.PAYLOAD_TIDY

    logger.debug("OUTPUT is \n" + Globals.OUTPUT)


def post_push_comment(base_url: str, diff_only: bool, user_id: int):
    """POST action's results for a push event.

    Args:
        base_url: The root of the url used to interact with the REST API via `requests`.
        diff_only: A flag that forces focus on only changes in the event's diff info.
        user_id: The user's account ID number.
    """
    comments_url = base_url + f"commits/{GITHUB_SHA}/comments"
    remove_bot_comments(comments_url, user_id)

    if not diff_only:
        payload = json.dumps({"body": Globals.OUTPUT})
        logger.debug("payload body:\n" + json.dumps({"body": Globals.OUTPUT}, indent=2))

    Globals.response_buffer = requests.post(
        comments_url, headers=API_HEADERS, data=payload
    )

    logger.info(
        f"Got {Globals.response_buffer.status_code} response from POSTing comment",
    )


def post_pr_comment(base_url: str, diff_only: bool, user_id: int):
    """POST action's results for a push event.

    Args:
        base_url: The root of the url used to interact with the REST API via `requests`.
        diff_only: A flag that forces focus on only changes in the event's diff info.
        user_id: The user's account ID number.
    """
    comments_url = base_url + f'issues/{Globals.EVENT_PAYLOAD["number"]}/comments'
    remove_bot_comments(comments_url, user_id)
    reviews_url = base_url + f'pulls/{Globals.EVENT_PAYLOAD["number"]}/'
    review_id = get_review_id(reviews_url + "reviews", user_id)

    payload = None  # scoped placeholder for posted output
    if not diff_only:
        payload = json.dumps({"body": Globals.OUTPUT})
        logger.debug("payload body:\n" + json.dumps({"body": Globals.OUTPUT}, indent=2))
    else:
        payload = list_diff_comments()
    if review_id is not None:
        if not diff_only:
            Globals.response_buffer = requests.put(
                reviews_url + f"reviews/{review_id}", headers=API_HEADERS, data=payload
            )
            logger.info(
                f"Got {Globals.response_buffer.status_code} from "
                f"PUT review {review_id} update"
            )
        else:
            logger.info(f"Posting {len(payload)} comments")
            for i, body in enumerate(payload):
                Globals.response_buffer = requests.post(
                    reviews_url + "comments", headers=API_HEADERS, data=json.dumps(body)
                )
                logger.info(
                    f"Got {Globals.response_buffer.status_code} from "
                    f"PUT review comment {i}"
                )
                logger.debug(json.dumps(body))
    else:
        raise RuntimeError("Could not create or find a review made by the bot")


def post_results(diff_only: bool, user_id: int = 41898282):
    """POST action's results using REST API.

    Args:
        diff_only: A flag that forces focus on only changes in the event's diff info.
        user_id: The user's account ID number. Defaults to the generic bot's ID.
    """

    if GITHUB_TOKEN is None:
        logger.error("The GITHUB_TOKEN is required!")
        sys.exit(set_exit_code(1))

    base_url = f"{GITHUB_API_URL}/repos/{GITHUB_REPOSITORY}/"
    if GITHUB_EVENT_NAME == "pull_request":
        post_pr_comment(base_url, diff_only, user_id)
    elif GITHUB_EVENT_NAME == "push":
        post_push_comment(base_url, diff_only, user_id)


def main():
    """The main script."""

    # The parsed CLI args
    args = cli_arg_parser.parse_args()

    # set logging verbosity
    logger.setLevel(int(args.verbosity))

    # change working directory
    os.chdir(args.repo_root)

    get_list_of_changed_files()
    filter_out_non_source_files(args.extensions, args.diff_only)
    verify_files_are_present()
    capture_clang_tools_output(
        args.version,
        args.tidy_checks,
        args.style,
        args.diff_only
    )
    set_exit_code(0)
    post_results(args.diff_only)  # 14963867 is user id for 2bndy5


if __name__ == "__main__":
    main()
