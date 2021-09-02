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
import logging
import requests
import unidiff
from . import Globals, GlobalParser
from .clang_tidy_yml import parse_tidy_suggestions_yml as parse_tidy_advice
from .clang_tidy import parse_tidy_output
from .clang_format_xml import parse_format_replacements_xml as parse_fmt_advice

try:
    from rich.logging import RichHandler

    logging.basicConfig(
        format="%(name)s: %(message)s",
        handlers=[RichHandler(show_time=False)],
    )

except ImportError:
    print("rich module not found")
    logging.basicConfig()

#: The logging.Logger object used for outputing data.
logger = logging.getLogger("CPP Linter")

# global constant variables
GITHUB_EVEN_PATH = os.getenv("GITHUB_EVENT_PATH", "event_payload.json")
GITHUB_API_URL = os.getenv("GITHUB_API_URL", "https://api.github.com")
GITHUB_REPOSITORY = os.getenv("GITHUB_REPOSITORY", "2bndy5/cpp-linter-action")
GITHUB_SHA = os.getenv("GITHUB_SHA", "293af27ec15d6094a5308fe655a7e111e5b8721a")
GITHUB_EVENT_NAME = os.getenv("GITHUB_EVENT_NAME", "pull_request")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", os.getenv("GIT_REST_API", None))
API_HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json",
}

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
    "modernize-*,clang-analyzer-*,cppcoreguidelines-*'. See also clang-tidy docs for more info.",
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


def set_exit_code(override: int=None):
    """Set the action's exit code.

    Args:
        override: The number to use when overriding the action's logic."""
    exit_code = override if override is not None else bool(Globals.OUTPUT)
    print(f"::set-output name=checks-failed::{exit_code}")
    return exit_code


def get_list_of_changed_files():
    """Fetch the JSON payload of the event's changed files. Sets the
    [`FILES`][python_action.__init__.Globals.FILES] &
    [`DIFF`][python_action.__init__.Globals.DIFF] attributes."""
    logger.info(f"processing {GITHUB_EVENT_NAME} event")
    with open(GITHUB_EVEN_PATH, "r", encoding="utf-8") as payload:
        Globals.EVENT_PAYLOAD = json.load(payload)
        logger.log(9, json.dumps(Globals.EVENT_PAYLOAD))

    Globals.FILES_LINK = f"{GITHUB_API_URL}/repos/{GITHUB_REPOSITORY}/"
    if GITHUB_EVENT_NAME == "pull_request":
        Globals.FILES_LINK += f"pulls/{Globals.EVENT_PAYLOAD['number']}"
        Globals.response_buffer = requests.get(
            Globals.FILES_LINK,
            headers={"Accept": "application/vnd.github.v3.diff"},
        )
        logger.info(
            f"Got {Globals.response_buffer.status_code} from diff request for PR #"
            f"{Globals.EVENT_PAYLOAD['number']}"
        )
        Globals.DIFF = unidiff.PatchSet(Globals.response_buffer.text)
        Globals.FILES_LINK += "/files"

    elif GITHUB_EVENT_NAME == "push":
        Globals.FILES_LINK += f"commits/{GITHUB_SHA}"
        Globals.response_buffer = requests.get(
            Globals.FILES_LINK,
            headers={"Accept": "application/vnd.github.v3.diff"},
        )
        logger.info(
            f"Got {Globals.response_buffer.status_code} from diff request for commit {GITHUB_SHA}"
        )
        Globals.DIFF = unidiff.PatchSet(Globals.response_buffer.text)
    else:
        logger.warn("triggered on unsupported event.")
        sys.exit(set_exit_code(0))
    logger.info("Fetching files list from url: " + Globals.FILES_LINK)
    Globals.FILES = requests.get(Globals.FILES_LINK).json()
    # logger.log(9, "files json:\n" + json.dumps(Globals.FILES, indent=2))


def filter_out_non_source_files(ext_list: str):
    """Exclude undesired files (specified by user input 'extensions'). This filter
    applies to the event's [`FILES`][python_action.__init__.Globals.FILES] &
    [`DIFF`][python_action.__init__.Globals.DIFF] attributes.

    Args:
        ext_list: A comma-separated `str` of extensions that are concerned.

    !!! note
        This will exit early when nothing left to do.
    """
    ext_list = ext_list.split(",")
    files = []
    for file in (
        Globals.FILES if GITHUB_EVENT_NAME == "pull_request" else Globals.FILES["files"]
    ):
        extension = re.search("\.\w+$", file["filename"])
        if extension is not None and extension.group(0)[1:] in ext_list:
            files.append(file)
        else:
            # remove this file from the diff also
            for i, diff in enumerate(Globals.DIFF):
                if diff.target_file[2:] == file["filename"]:
                    del Globals.DIFF[i]
                    break

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
        if not os.path.exists(file["filename"]):
            logger.info(f'Downloading file from url: {file["raw_url"]}')
            download = requests.get(file["raw_url"])
            with open(
                os.path.split(file["filename"])[1], "w", encoding="utf-8"
            ) as temp:
                temp.write(download)


def remove_duplicate_comments(comments_url: str, user_id: int):
    """Traverse the list of comments made by a specific user
    and remove all but the 1st.

    Args:
        comments_url: The url used to fetch the comments.
        user_id: The user's account id number.
    """
    first_comment_id = 0
    comments = json.loads(requests.get(comments_url).text)
    for i, comment in enumerate(comments):
        # only serach for comments from the user's ID and
        # whose comment body begins with a specific html comment
        if (
            int(comment["user"]["id"]) == user_id
            # the specific html comment is our action's name
            and comment["body"].startswith("<!-- cpp linter action -->")
        ):
            first_comment_id = comment["id"]  # capture id
            if i < len(comments) - 1:
                # remove other outdated comments but don't remove the last comment
                Globals.response_buffer = requests.delete(
                    comment["url"],
                    headers=API_HEADERS,
                )
                logger.info(
                    f"Got {Globals.response_buffer.status_code} from DELETE "
                    f"{comment['url']}"
                )
        logger.debug(
            f'comment id {comment["id"]} from user {comment["user"]["login"]}'
            f' ({comment["user"]["id"]})'
        )
    # print("Comments:", comments)
    with open("comments.json", "w", encoding="utf-8") as json_comments:
        json.dump(comments, json_comments, indent=4)
    return (first_comment_id, len(comments))


def dismiss_stale_reviews(reviews_url: str, user_id: int):
    """Dismiss all stale reviews (only the ones made by our bot).

    Args:
        reviews_url: The url used to fetch the review comments.
        user_id: The user's account id number.
    """
    logger.info(f"  review_url: {reviews_url}")
    Globals.response_buffer = requests.get(reviews_url)
    review_id = 0
    reviews = Globals.response_buffer.json()
    if not reviews:
        # create a PR review
        Globals.response_buffer = requests.post(
            reviews_url,
            headers=API_HEADERS,
            data=json.dumps(
                {
                    "body": "<!-- cpp linter action -->\nTo be continued...",
                    "event": "COMMENTED",
                }
            ),
        )
        logger.info(
            "Got %d from POSTing new(/temp) PR review",
            Globals.response_buffer.status_code,
        )
        Globals.response_buffer = requests.get(reviews_url)
        reviews = Globals.response_buffer.json()

    for i, review in enumerate(reviews):
        if int(review["user"]["id"]) == user_id and review["body"].startswith(
            "<!-- cpp linter action -->"
        ):
            review_id = int(review["id"])
            if i < len(reviews) - 1:
                Globals.response_buffer = requests.put(
                    f'{reviews_url}/{review["id"]}',
                    headers=API_HEADERS,
                    data=json.dumps({"body": "This outdated comment has been edited."}),
                )
                logger.info(
                    "Got {} from PATCHing review {} by {}".format(
                        Globals.response_buffer.status_code,
                        review["id"],
                        review["user"]["login"],
                    )
                )

    logger.info(f"   review_id: {review_id}")
    return review_id


def capture_clang_tools_output(version: str, checks: str, style: str):
    """Execute and capture all output from clang-tidy and clang-format. This aggregates
    results in the [`OUTPUT`][python_action.__init__.Globals.OUTPUT].

    Args:
        version: The version of clang-tidy to run.
        checks: The `str` of comma-separated regulate expressions that describe
            the desired clang-tidy checks to be enabled/configured.
        style: The clang-format style rules to adhere. Set this to 'file' to
            use the relative-most .clang-format configuration file.
    """
    for file in (
        Globals.FILES if GITHUB_EVENT_NAME == "pull_request" else Globals.FILES["files"]
    ):
        filename = file["filename"]
        if not os.path.exists(file["filename"]):
            filename = os.path.split(file["raw_url"])[1]
        logger.info(f"Performing checkup on {filename}")

        # run clang-tidy
        cmds = [f"clang-tidy-{version}"]
        if checks:
            cmds.append(f"-checks={checks}")
        cmds.append("--export-fixes=clang_tidy_output.yml")
        cmds.append(filename)
        with open("clang_tidy_report.txt", "w", encoding="utf-8") as f_out:
            subprocess.run(cmds, stdout=f_out)
        # get clang-tidy fixes from yml
        parse_tidy_advice()

        # run clang-format
        cmds = [
            f"clang-format-{version}",
            f"-style={style}",
            "--output-replacements-xml",
            filename,
        ]

        with open("clang_format_output.xml", "w", encoding="utf-8") as f_out:
            subprocess.run(cmds, stderr=f_out, stdout=f_out)

        if os.path.getsize("clang_tidy_report.txt"):
            # get clang-tidy fixes from stout
            parse_tidy_output()
            if Globals.PAYLOAD_TIDY:
                Globals.PAYLOAD_TIDY += "<hr></details>"
            Globals.PAYLOAD_TIDY += f"<details><summary>{filename}</summary><br>\n"
            for fix in GlobalParser.tidy_notes:
                Globals.PAYLOAD_TIDY += repr(fix)
            GlobalParser.tidy_notes.clear()

        if os.path.getsize("clang_format_output.xml"):
            # parse format suggestions from clang-format (exported in XML file)
            parse_fmt_advice(filename)
            if not Globals.OUTPUT:
                Globals.OUTPUT = "<!-- cpp linter action -->\n## :scroll: "
                Globals.OUTPUT += "Run `clang-format` on the following files\n"
            Globals.OUTPUT += f"- [ ] {file['filename']}\n"

    if Globals.PAYLOAD_TIDY:
        Globals.OUTPUT += "\n---\n## :speech_balloon: Output from `clang-tidy`\n"
        Globals.OUTPUT += Globals.PAYLOAD_TIDY + "</details>"

    logger.log(9, "OUTPUT is \n" + Globals.OUTPUT)


def post_results(user_id: int=41898282):
    """POST action's results using REST API.

    Args:
        user_id: The user's account ID number. Defaults to the generic bot's ID.
    """
    comments_url = ""
    reviews_url = ""
    review_id = 0
    comment_id = 0
    commit_url = f"{GITHUB_API_URL}/repos/{GITHUB_REPOSITORY}/"
    if GITHUB_EVENT_NAME == "pull_request":
        comments_url = commit_url + f'issues/{Globals.EVENT_PAYLOAD["number"]}/comments'
        reviews_url = commit_url + f'pulls/{Globals.EVENT_PAYLOAD["number"]}/reviews'
    elif GITHUB_EVENT_NAME == "push":
        comments_url = commit_url + f"commits/{GITHUB_SHA}" + "/comments"

    # 41898282 is the bot's ID (used for all github actions' generic bot)
    comment_id, comments_cnt = remove_duplicate_comments(comments_url, user_id)
    logger.info(f"Number of Comments = {comments_cnt}")

    if GITHUB_TOKEN is None:
        logger.error("The GITHUB_TOKEN is required!")
        sys.exit(set_exit_code(1))

    payload = json.dumps({"body": Globals.OUTPUT})
    # logger.log(9, "payload body:\n" + json.dumps({"body": Globals.OUTPUT}, indent=2))

    if GITHUB_EVENT_NAME == "push":
        commit_url += f"comments/{comment_id}"
    else:
        commit_url += f"issues/comments/{comment_id}"
    logger.info("comments_url: " + comments_url)

    if reviews_url:
        review_id = dismiss_stale_reviews(reviews_url, user_id)

        if comment_id:
            Globals.response_buffer = requests.delete(
                commit_url,
                headers=API_HEADERS,
            )
            logger.info(
                f"Got {Globals.response_buffer.status_code} from DELETE {comments_url}"
            )

        Globals.response_buffer = requests.put(
            reviews_url + f"/{review_id}", headers=API_HEADERS, data=payload
        )
        logger.info(
            f"Got {Globals.response_buffer.status_code} from PUT review {review_id} update"
        )
    else:
        if comment_id:
            logger.info("  commit_url: " + commit_url)
            Globals.response_buffer = requests.patch(
                commit_url, headers=API_HEADERS, data=payload
            )
        else:
            Globals.response_buffer = requests.post(
                comments_url, headers=API_HEADERS, data=payload
            )

        logger.info(
            "Got %d response from %sing comment",
            Globals.response_buffer.status_code,
            "PATCH" if comment_id else "POST",
        )


def main():
    """The main script."""

    # The parsed CLI args
    args = cli_arg_parser.parse_args()

    logger.setLevel(int(args.verbosity))
    logger.info("processing run number %d", int(os.getenv("GITHUB_RUN_NUMBER", "0")))

    # change working directory
    os.chdir(args.repo_root)

    get_list_of_changed_files()
    filter_out_non_source_files(args.extensions)
    verify_files_are_present()
    capture_clang_tools_output(args.version, args.tidy_checks, args.style)
    set_exit_code(0)
    # post_results()  # leave param blank to look for the generic github action bot
    post_results(14963867)  # 14963867 is user id for 2bndy5


if __name__ == "__main__":
    main()
