"""Run clang-tidy and clang-format on a list of changed files provided by GitHub's
REST API. If executed from command-line, then [`main()`][python_action.run.main] is
the entrypoint.

!!! info "See Also"
    - [github rest API reference for pulls](
        https://docs.github.com/en/rest/reference/pulls)
    - [github rest API reference for repos](
        https://docs.github.com/en/rest/reference/repos)
    - [github rest API reference for issues](
        https://docs.github.com/en/rest/reference/issues)
"""
import subprocess
import os
import sys
import re
import argparse
import configparser
import json
import requests
from . import (
    Globals,
    GlobalParser,
    logging,
    logger,
    GITHUB_TOKEN,
    GITHUB_SHA,
    API_HEADERS,
    log_response_msg,
)

from .clang_tidy_yml import parse_tidy_suggestions_yml
from .clang_format_xml import parse_format_replacements_xml
from .clang_tidy import parse_tidy_output
from .thread_comments import remove_bot_comments, list_diff_comments  # , get_review_id


# global constant variables
GITHUB_EVEN_PATH = os.getenv("GITHUB_EVENT_PATH", "event_payload.json")
GITHUB_API_URL = os.getenv("GITHUB_API_URL", "https://api.github.com")
GITHUB_REPOSITORY = os.getenv("GITHUB_REPOSITORY", "2bndy5/cpp-linter-action")
GITHUB_EVENT_NAME = os.getenv("GITHUB_EVENT_NAME", "pull_request")

# setup CLI args
cli_arg_parser = argparse.ArgumentParser(
    description=__doc__[: __doc__.find("If executed from")]
)
cli_arg_parser.add_argument(
    "-v",
    "--verbosity",
    default="10",
    help="The logging level. Defaults to level 20 (aka 'logging.INFO').",
)
cli_arg_parser.add_argument(
    "-s",
    "--style",
    default="llvm",
    help="The style rules to use (defaults to 'llvm'). Set this to 'file' to have "
    "clang-format use the closest relative .clang-format file.",
)
cli_arg_parser.add_argument(
    "-c",
    "--tidy-checks",
    default="boost-*,bugprone-*,performance-*,readability-*,portability-*,modernize-*,"
    "clang-analyzer-*,cppcoreguidelines-*",
    help="A string of regex-like patterns specifying what checks clang-tidy will use. "
    "This defaults to %(default)s. See also clang-tidy docs for more info.",
)
cli_arg_parser.add_argument(
    "-V",
    "--version",
    default="10",
    help="The desired version of the clang tools to use. Accepted options are strings "
    "which can be 6.0, 7, 8, 9, 10, 11, 12. Defaults to %(default)s.",
)
cli_arg_parser.add_argument(
    "-e",
    "--extensions",
    default="c,h,C,H,cpp,hpp,cc,hh,c++,h++,cxx,hxx",
    help="The file extensions to run the action against. This comma-separated string "
    "defaults to %(default)s.",
)
cli_arg_parser.add_argument(
    "-r",
    "--repo-root",
    default=".",
    help="The relative path to the repository root directory. The default value "
    "'%(default)s' is relative to the runner's GITHUB_WORKSPACE environment variable.",
)
cli_arg_parser.add_argument(
    "-i",
    "--ignore",
    # default=[],
    # nargs="*",
    help="Set this option with paths to ignore. In the case of multiple "
    "paths, you can set this option (multiple times) for each path. This can "
    "also have files, but the file's relative path has to be specified as well "
    "with the filename.",
)
cli_arg_parser.add_argument(
    "--lines-changed-only",
    default="false",
    type=lambda input: input.lower() == "true",
    help="Set this option to 'true' to only analyse changes in the event's diff. "
    "Defaults to %(default)s.",
)
cli_arg_parser.add_argument(
    "--files-changed-only",
    default="true",
    type=lambda input: input.lower() == "true",
    help="Set this option to 'false' to analyse any source files in the repo. "
    "Defaults to %(default)s.",
)


def set_exit_code(override: int = None) -> int:
    """Set the action's exit code.

    Args:
        override: The number to use when overriding the action's logic.

    Returns:
        The exit code that was used. If the `override` parameter was not passed,
        then this value will describe (like a bool value) if any checks failed.
    """
    exit_code = override if override is not None else bool(Globals.OUTPUT)
    print(f"::set-output name=checks-failed::{exit_code}")
    return exit_code


# setup a separate logger for using github log commands
log_commander = logger.getChild("LOG COMMANDER")  # create a child of our logger obj
log_commander.setLevel(logging.DEBUG)  # be sure that log commands are output
console_handler = logging.StreamHandler()  # Create special stdout stream handler
console_handler.setFormatter(logging.Formatter("%(message)s"))  # no formatted log cmds
log_commander.addHandler(console_handler)  # Use special handler for log_commander
log_commander.propagate = False  # prevent duplicate messages in the parent logger obj


def start_log_group(name: str) -> None:
    """Begin a callapsable group of log statements.

    Argrs:
        name: The name of the callapsable group
    """
    log_commander.fatal("::group::%s", name)


def end_log_group() -> None:
    """End a callapsable group of log statements."""
    log_commander.fatal("::endgroup::")


def is_file_in_list(paths: list, file_name: str) -> bool:
    """Detirmine if a file is specified in a list of paths and/or filenames.

    Args:
        paths: A list of specified paths to compare with. This list can contain a
            specified file, but the file's path must be included as part of the
            filename.
        file_name: The file's path & name being sought in the `paths` list.
    Returns:
        - True if `file_name` is in the `paths` list.
        - False if `file_name` is not in the `paths` list.
    """
    for path in paths:
        result = os.path.commonpath([path, file_name]).replace(os.sep, "/")
        if result == path:
            logger.debug('"%s" is in the specified domain "%s"', file_name, path)
            return True
    return False


def get_list_of_changed_files() -> None:
    """Fetch the JSON payload of the event's changed files. Sets the
    [`FILES`][python_action.__init__.Globals.FILES] attribute."""
    files_link = f"{GITHUB_API_URL}/repos/{GITHUB_REPOSITORY}/"
    if GITHUB_EVENT_NAME == "pull_request":
        files_link += f"pulls/{Globals.EVENT_PAYLOAD['number']}/files"
    elif GITHUB_EVENT_NAME == "push":
        files_link += f"commits/{GITHUB_SHA}"
    else:
        logger.warning("triggered on unsupported event.")
        sys.exit(set_exit_code(0))
    logger.info("Fetching files list from url: %s", files_link)
    Globals.FILES = requests.get(files_link).json()


def filter_out_non_source_files(
    ext_list: list, ignored: list, not_ignored: list, lines_changed_only: bool
) -> bool:
    """Exclude undesired files (specified by user input 'extensions'). This filter
    applies to the event's [`FILES`][python_action.__init__.Globals.FILES] attribute.

    Args:
        ext_list: A list of file extensions that are to be examined.
        ignored: A list of paths to explicitly ignore.
        not_ignored: A list of paths to explicitly not ignore.
        lines_changed_only: A flag that forces focus on only changes in the event's
            diff info.

    Returns:
        True if there are files to check. False will invoke a early exit (in
        [`main()`][python_action.run.main()]) when no files to be checked.
    """
    files = []
    for file in (
        Globals.FILES if GITHUB_EVENT_NAME == "pull_request" else Globals.FILES["files"]
    ):
        extension = re.search("\.\w+$", file["filename"])
        if (
            extension is not None
            and extension.group(0)[1:] in ext_list
            and not file["status"].endswith("removed")
            and (
                not is_file_in_list(ignored, file["filename"])
                or is_file_in_list(not_ignored, file["filename"])
            )
        ):
            if lines_changed_only and "patch" in file.keys():
                # get diff details for the file's changes
                line_filter = {
                    "name": file["filename"].replace("/", os.sep),
                    "lines": [],
                }
                file["diff_line_map"], line_numb_in_diff = ({}, 0)
                # diff_line_map is a dict for which each
                #     - key is the line number in the file
                #     - value is the line's "position" in the diff
                for i, line in enumerate(file["patch"].splitlines()):
                    if line.startswith("@@ -"):
                        changed_hunk = line[line.find(" +") + 2 : line.find(" @@")]
                        changed_hunk = changed_hunk.split(",")
                        start_line = int(changed_hunk[0])
                        hunk_length = int(changed_hunk[1])
                        line_filter["lines"].append(
                            [start_line, hunk_length + start_line]
                        )
                        line_numb_in_diff = start_line
                    elif not line.startswith("-"):
                        file["diff_line_map"][line_numb_in_diff] = i
                        line_filter["lines"][-1][1] = line_numb_in_diff
                        line_numb_in_diff += 1
                file["line_filter"] = line_filter
            elif lines_changed_only:
                continue
            files.append(file)

    if files:
        logger.info(
            "Giving attention to the following files:\n\t%s",
            "\n\t".join([f["filename"] for f in files]),
        )
        if GITHUB_EVENT_NAME == "pull_request":
            Globals.FILES = files
        else:
            Globals.FILES["files"] = files
        if not os.getenv("CI"):  # if not executed on a github runner
            with open(
                ".cpp_linter_action_changed_files.json", "w", encoding="utf-8"
            ) as temp:
                # dump altered json of changed files
                json.dump(Globals.FILES, temp, indent=2)
    else:
        logger.info("No source files need checking!")
        return False
    return True


def verify_files_are_present() -> None:
    """Download the files if not present.

    !!! hint
        This function assumes the working directory is the root of the invoking
        repository. If files are not found, then they are downloaded to the working
        directory. This is bad for files with the same name from different folders.
    """
    for file in (
        Globals.FILES if GITHUB_EVENT_NAME == "pull_request" else Globals.FILES["files"]
    ):
        file_name = file["filename"].replace("/", os.sep)
        if not os.path.exists(file_name):
            logger.warning("Could not find %s! Did you checkout the repo?", file_name)
            logger.info("Downloading file from url: %s", file["raw_url"])
            Globals.response_buffer = requests.get(file["raw_url"])
            with open(os.path.split(file_name)[1], "w", encoding="utf-8") as temp:
                temp.write(Globals.response_buffer.text)


def list_source_files(ext_list: str, ignored_paths: list, not_ignored: list) -> bool:
    """Make a list of source files to be checked. The resulting list is stored in
    [`FILES`][Global.FILES].

    Args:
        ext_list: A comma-separated `str` of extensions that are concerned.
        ignored_paths: A list of paths to explicitly ignore.
        not_ignored: A list of paths to explicitly not ignore.

    Returns:
        True if there are files to check. False will invoke a early exit (in
        [`main()`][python_action.run.main()]) when no files to be checked.
    """
    if os.path.exists(".gitmodules"):
        submodules = configparser.ConfigParser()
        submodules.read(".gitmodules")
        for module in submodules.sections():
            logger.info(
                "Apending submodule to ignored paths: %s", submodules[module]["path"]
            )
            ignored_paths.append(submodules[module]["path"])

    root_path = os.getcwd()
    for dirpath, _, filenames in os.walk(root_path):
        path = dirpath.replace(root_path, "").lstrip(os.sep)
        if path.startswith("."):
            # logger.debug("Skipping \"%s\"", path)
            continue  # skip sources in hidden directories
        logger.debug('Crawling "./%s"', path)
        for file in filenames:
            if file.find(".") > 0 and file.split(".")[1] in ext_list:
                file_path = os.path.join(path, file)
                logger.debug("%s is a source file", file_path)
                if not is_file_in_list(ignored_paths, file_path) or is_file_in_list(
                    not_ignored, file_path
                ):
                    Globals.FILES.append({"filename": file_path})

    if Globals.FILES:
        logger.info(
            "Giving attention to the following files:\n\t%s",
            "\n\t".join([f["filename"] for f in Globals.FILES]),
        )
    else:
        logger.info("No source files found.")  # this might need to be warning
        return False
    return True


def run_clang_tidy(
    filename: str, file_obj: dict, version: str, checks: str, lines_changed_only: bool
) -> None:
    """Run clang-tidy on a certain file.

    Args:
        filename: The name of the local file to run clang-tidy on.
        file_obj: JSON info about the file.
        version: The version of clang-tidy to run.
        checks: The `str` of comma-separated regulate expressions that describe
            the desired clang-tidy checks to be enabled/configured.
        lines_changed_only: A flag that forces focus on only changes in the event's
            diff info.
    """
    cmds = [f"clang-tidy-{version}"]
    if sys.platform.startswith("win32"):
        cmds = ["clang-tidy"]
    if checks:
        cmds.append(f"-checks={checks}")
    cmds.append("--export-fixes=clang_tidy_output.yml")
    # cmds.append(f"--format-style={style}")
    if lines_changed_only:
        logger.info("line_filter = %s", json.dumps(file_obj["line_filter"]["lines"]))
        cmds.append(f"--line-filter={json.dumps([file_obj['line_filter']])}")
    cmds.append(filename.replace("/", os.sep))
    with open("clang_tidy_output.yml", "wb"):
        pass  # clear yml file's content before running clang-tidy
    results = subprocess.run(cmds, capture_output=True)
    with open("clang_tidy_report.txt", "wb") as f_out:
        f_out.write(results.stdout)
    logger.debug("Output from clang-tidy:\n%s", results.stdout.decode())
    if os.path.getsize("clang_tidy_output.yml"):
        parse_tidy_suggestions_yml()  # get clang-tidy fixes from yml
    if results.returncode:
        logger.warning(
            "%s raised the following error(s):\n%s", cmds[0], results.stderr.decode()
        )


def run_clang_format(
    filename: str, file_obj: dict, version: str, style: str, lines_changed_only: bool
) -> None:
    """Run clang-format on a certain file

    Args:
        filename: The name of the local file to run clang-format on.
        file_obj: JSON info about the file.
        version: The version of clang-format to run.
        style: The clang-format style rules to adhere. Set this to 'file' to
            use the relative-most .clang-format configuration file.
        lines_changed_only: A flag that forces focus on only changes in the event's
            diff info.
    """
    cmds = [
        "clang-format" + ("" if sys.platform.startswith("win32") else f"-{version}"),
        f"-style={style}",
        "--output-replacements-xml",
    ]
    if lines_changed_only:
        for line_range in file_obj["line_filter"]["lines"]:
            cmds.append(f"--lines={line_range[0]}:{line_range[1]}")
    cmds.append(filename.replace("/", os.sep))
    results = subprocess.run(cmds, capture_output=True)
    with open("clang_format_output.xml", "wb") as f_out:
        f_out.write(results.stdout)
    if results.stdout:
        logger.debug("clang-format has suggestions.")
    if results.returncode:
        logger.warning(
            "%s raised the following error(s):\n%s", cmds[0], results.stderr.decode()
        )


def capture_clang_tools_output(
    version: str, checks: str, style: str, lines_changed_only: bool
):
    """Execute and capture all output from clang-tidy and clang-format. This aggregates
    results in the [`OUTPUT`][python_action.__init__.Globals.OUTPUT].

    Args:
        version: The version of clang-tidy to run.
        checks: The `str` of comma-separated regulate expressions that describe
            the desired clang-tidy checks to be enabled/configured.
        style: The clang-format style rules to adhere. Set this to 'file' to
            use the relative-most .clang-format configuration file.
        lines_changed_only: A flag that forces focus on only changes in the event's
            diff info.
    """
    for file in (
        Globals.FILES
        if GITHUB_EVENT_NAME == "pull_request" or isinstance(Globals.FILES, list)
        else Globals.FILES["files"]
    ):
        filename = file["filename"]
        if not os.path.exists(file["filename"]):
            filename = os.path.split(file["raw_url"])[1]
        start_log_group(f"Performing checkup on {filename}")
        run_clang_tidy(filename, file, version, checks, lines_changed_only)
        run_clang_format(filename, file, version, style, lines_changed_only)
        end_log_group()
        if os.path.getsize("clang_tidy_report.txt"):
            parse_tidy_output()  # get clang-tidy fixes from stdout
            if Globals.PAYLOAD_TIDY:
                Globals.PAYLOAD_TIDY += "<hr></details>"
            Globals.PAYLOAD_TIDY += f"<details><summary>{filename}</summary><br>\n"
            for fix in GlobalParser.tidy_notes:
                Globals.PAYLOAD_TIDY += repr(fix)
            GlobalParser.tidy_notes.clear()

        if os.path.getsize("clang_format_output.xml"):
            parse_format_replacements_xml(filename.replace("/", os.sep))
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


def post_push_comment(base_url: str, user_id: int) -> bool:
    """POST action's results for a push event.

    Args:
        base_url: The root of the url used to interact with the REST API via `requests`.
        user_id: The user's account ID number.

    Returns:
        A bool describing if the linter checks passed. This is used as the action's
        output value (a soft exit code).
    """
    comments_url = base_url + f"commits/{GITHUB_SHA}/comments"
    remove_bot_comments(comments_url, user_id)

    if Globals.OUTPUT:  # diff comments are not supported for push events (yet)
        payload = json.dumps({"body": Globals.OUTPUT})
        logger.debug("payload body:\n%s", json.dumps({"body": Globals.OUTPUT}))
        Globals.response_buffer = requests.post(
            comments_url, headers=API_HEADERS, data=payload
        )
        logger.info(
            "Got %d response from POSTing comment", Globals.response_buffer.status_code
        )
        log_response_msg()
    return bool(Globals.OUTPUT)


def post_diff_comments(base_url: str, user_id: int) -> bool:
    """Post comments inside a unified diff (only PRs are supported).

    Args:
        base_url: The root of the url used to interact with the REST API via `requests`.
        user_id: The user's account ID number.

    Returns:
        A bool describing if the linter checks passed. This is used as the action's
        output value (a soft exit code).
    """
    comments_url = base_url + "pulls/comments/"  # for use with comment_id
    payload = list_diff_comments()
    logger.info("Posting %d comments", len(payload))

    # uncomment the next 3 lines for debug output without posting a comment
    # for i, comment in enumerate(payload):
    #     logger.debug("comments %d: %s", i, json.dumps(comment, indent=2))
    # return

    # get existing review comments
    reviews_url = base_url + f'pulls/{Globals.EVENT_PAYLOAD["number"]}/'
    Globals.response_buffer = requests.get(reviews_url + "comments")
    existing_comments = json.loads(Globals.response_buffer.text)
    # filter out comments not made by our bot
    for index, comment in enumerate(existing_comments):
        if not comment["body"].startswith("<!-- cpp linter action -->"):
            del existing_comments[index]

    # conditionally post comments in the diff
    for i, body in enumerate(payload):
        # check if comment is already there
        already_posted = False
        comment_id = None
        for comment in existing_comments:
            if (
                int(comment["user"]["id"]) == user_id
                and comment["line"] == body["line"]
                and comment["path"] == payload[i]["path"]
            ):
                already_posted = True
                if comment["body"] != body["body"]:
                    comment_id = str(comment["id"])  # use this to update comment
                else:
                    break
        if already_posted and comment_id is None:
            logger.info("comment %d already posted", i)
            continue  # don't bother reposting the same comment

        # update ot create a review comment (in the diff)
        logger.debug("Payload %d body = %s", i, json.dumps(body))
        if comment_id is not None:
            Globals.response_buffer = requests.patch(
                comments_url + comment_id,
                headers=API_HEADERS,
                data=json.dumps({"body": body["body"]}),
            )
            logger.info(
                "Got %d from PATCHing comment %d (%d)",
                Globals.response_buffer.status_code,
                i,
                comment_id,
            )
            log_response_msg()
        else:
            Globals.response_buffer = requests.post(
                reviews_url + "comments", headers=API_HEADERS, data=json.dumps(body)
            )
            logger.info(
                "Got %d from POSTing review comment %d",
                Globals.response_buffer.status_code,
                i,
            )
            log_response_msg()
    return bool(payload)


def post_pr_comment(base_url: str, user_id: int) -> bool:
    """POST action's results for a push event.

    Args:
        base_url: The root of the url used to interact with the REST API via `requests`.
        user_id: The user's account ID number.

    Returns:
        A bool describing if the linter checks passed. This is used as the action's
        output value (a soft exit code).
    """
    comments_url = base_url + f'issues/{Globals.EVENT_PAYLOAD["number"]}/comments'
    remove_bot_comments(comments_url, user_id)
    payload = ""
    if Globals.OUTPUT:
        payload = json.dumps({"body": Globals.OUTPUT})
        logger.debug(
            "payload body:\n%s", json.dumps({"body": Globals.OUTPUT}, indent=2)
        )
        Globals.response_buffer = requests.post(
            comments_url, headers=API_HEADERS, data=payload
        )
        logger.info("Got %d from POSTing comment", Globals.response_buffer.status_code)
        log_response_msg()
    return bool(payload)


def post_results(use_diff_comments: bool, user_id: int = 41898282):
    """Post action's results using REST API.

    Args:
        use_diff_comments: This flag enables making/updating comments in the PR's diff
            info.
        user_id: The user's account ID number. Defaults to the generic bot's ID.
    """
    if not GITHUB_TOKEN:
        logger.error("The GITHUB_TOKEN is required!")
        sys.exit(set_exit_code(1))

    base_url = f"{GITHUB_API_URL}/repos/{GITHUB_REPOSITORY}/"
    checks_passed = True
    if GITHUB_EVENT_NAME == "pull_request":
        checks_passed = post_pr_comment(base_url, user_id)
        if use_diff_comments:
            checks_passed = post_diff_comments(base_url, user_id)
    elif GITHUB_EVENT_NAME == "push":
        checks_passed = post_push_comment(base_url, user_id)
    set_exit_code(1 if checks_passed else 0)


def main():
    """The main script."""

    # The parsed CLI args
    args = cli_arg_parser.parse_args()

    # set logging verbosity
    logger.setLevel(int(args.verbosity))

    # prepare ignored paths list
    args.ignore = args.ignore.split(";")
    ignored, not_ignored = ([], [])
    for path in args.ignore:
        path = path.lstrip("./")  # relative dir is assumed
        path = path.strip()  # strip leading/trailing spaces
        path = path.strip("'").strip("\"")  # strip leading/trailing quotes
        if path.startswith("!"):
            not_ignored.append(path[1:])
        else:
            ignored.append(path)

    # prepare extensions list
    args.extensions = args.extensions.split(",")

    logger.info("processing %s event", GITHUB_EVENT_NAME)

    # load event's json info about the workflow run
    with open(GITHUB_EVEN_PATH, "r", encoding="utf-8") as payload:
        Globals.EVENT_PAYLOAD = json.load(payload)
    if logger.getEffectiveLevel() <= logging.DEBUG:
        start_log_group("Event json from the runner")
        logger.debug(json.dumps(Globals.EVENT_PAYLOAD))
        end_log_group()

    # change working directory
    os.chdir(args.repo_root)

    start_log_group("Get list of specified source files")
    if ignored:
        logger.info(
            "Ignoring the following paths/files:\n\t%s",
            "\n\t".join(f for f in ignored),
        )
    if not_ignored:
        logger.info(
            "Not ignoring the following paths/files:\n\t%s",
            "\n\t".join(f for f in not_ignored),
        )
    exit_early = False
    if args.files_changed_only:
        get_list_of_changed_files()
        exit_early = not filter_out_non_source_files(
            args.extensions,
            ignored,
            not_ignored,
            args.lines_changed_only if args.files_changed_only else False,
        )
        if not exit_early:
            verify_files_are_present()
    else:
        exit_early = not list_source_files(args.extensions, ignored, not_ignored)
    end_log_group()
    if exit_early:
        sys.exit(set_exit_code(0))

    capture_clang_tools_output(
        args.version, args.tidy_checks, args.style, args.lines_changed_only
    )

    start_log_group("Posting comment(s)")
    # post_results(False)  # False is hard-coded to disable diff comments.
    end_log_group()


if __name__ == "__main__":
    main()
