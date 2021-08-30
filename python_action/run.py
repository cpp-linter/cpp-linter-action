"""Run clang-tidy and clang-format on a list of changed files provided by GitHub's
REST API."""
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

logger = logging.getLogger("CPP Linter")

# global constant variables
GITHUB_EVEN_PATH = os.getenv("GITHUB_EVENT_PATH", "event_payload.json")
GITHUB_API_URL = os.getenv("GITHUB_API_URL", "https://api.github.com")
GITHUB_REPOSITORY = os.getenv("GITHUB_REPOSITORY", "2bndy5/cpp-linter-action")
GITHUB_SHA = os.getenv("GITHUB_SHA", "0f216e2909e05f85d132b0896127e3026c13f27d")
GITHUB_EVENT_NAME = os.getenv("GITHUB_EVENT_NAME", "pull_request")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", os.getenv("GIT_REST_API", None))
API_HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json",
    # "Accept": "application/vnd.github.v3.diff",
}

# setup CLI args
cli_arg_parser = argparse.ArgumentParser(description=__doc__)
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


def set_exit_code(override=None):
    """Set the action's exit code."""
    exit_code = override if override is not None else bool(Globals.OUTPUT)
    print(f"::set-output name=checks-failed::{exit_code}")
    return exit_code


def get_list_of_changed_files():
    """Fetch the JSON payload of the event's changed files."""
    logger.info(f"processing {GITHUB_EVENT_NAME} event")
    with open(GITHUB_EVEN_PATH, "r", encoding="utf-8") as payload:
        Globals.EVENT_PAYLOAD = json.load(payload)
        logger.log(9, json.dumps(Globals.EVENT_PAYLOAD))

    Globals.FILES_LINK = f"{GITHUB_API_URL}/repos/{GITHUB_REPOSITORY}/"
    response = None
    if GITHUB_EVENT_NAME == "pull_request":
        Globals.FILES_LINK += f"pulls/{Globals.EVENT_PAYLOAD['number']}/files"
        response = requests.get(
            Globals.FILES_LINK.replace("/files", ""),
            headers={"Accept": "application/vnd.github.v3.diff"},
        )
        logger.info(
            f"Got {response.status_code} from diff request for PR #"
            f"{Globals.EVENT_PAYLOAD['number']}"
        )
        Globals.DIFF = unidiff.PatchSet(response.text)

    elif GITHUB_EVENT_NAME == "push":
        Globals.FILES_LINK += f"commits/{GITHUB_SHA}"
        response = requests.get(
            Globals.FILES_LINK,
            headers={"Accept": "application/vnd.github.v3.diff"},
        )
        logger.info(
            f"Got {response.status_code} from diff request for commit {GITHUB_SHA}"
        )
        Globals.DIFF = unidiff.PatchSet(response.text)
    else:
        logger.warn("triggered on unsupported event.")
        sys.exit(set_exit_code(0))
    logger.info("Fetching files list from url: " + Globals.FILES_LINK)
    Globals.FILES = requests.get(Globals.FILES_LINK).json()
    # logger.log(9, "files json:\n" + json.dumps(Globals.FILES, indent=2))


def filter_out_non_source_files(ext_list):
    """exclude undesired files (specified by user input 'extensions')"""
    ext_list = ext_list.split(",")
    files = []
    for file in (
        Globals.FILES if GITHUB_EVENT_NAME == "pull_request" else Globals.FILES["files"]
    ):
        extension = re.search("\.\w+$", file["filename"])
        if extension is not None and extension.group(0)[1:] in ext_list:
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
    """Download the files if not present. This function assumes the working directory
    is the root of the invoking repository."""
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
    and remove all but the 1st."""
    first_comment_id = 0
    comments = json.loads(requests.get(comments_url).text)
    for comment in comments:
        # only serach for comments from the user's ID and
        # whose comment body begins with a specific html comment
        if (
            int(comment["user"]["id"]) == user_id
            # the specific html comment is our action's name
            and comment["body"].startswith("<!-- cpp linter action -->")
        ):
            if not first_comment_id:
                # capture id and don't remove the first comment
                first_comment_id = comment["id"]
            else:
                # remove othre outdated comments
                response = requests.delete(
                    comment["url"],
                    headers=API_HEADERS,
                )
                logger.info(f"Got {response.status_code} from DELETE {comment['url']}")
        logger.debug(
            f'comment id {comment["id"]} from user {comment["user"]["login"]}'
            f' ({comment["user"]["id"]})'
        )
    # print("Comments:", comments)
    with open("comments.json", "w", encoding="utf-8") as json_comments:
        json.dump(comments, json_comments, indent=4)
    return first_comment_id


def dismiss_stale_reviews(reviews_url: str, user_id: int):
    """Dismiss all stale reviews (only the ones made by our bot)."""
    logger.info(f"  review_url: {reviews_url}")
    response = requests.get(reviews_url)
    review_id = 0
    reviews = response.json()
    if not reviews:
        # create a PR review
        response = requests.post(
            reviews_url,
            headers=API_HEADERS,
            data=json.dumps(
                {
                    "body": "<!-- cpp linter action -->\nTo be continued...",
                    "event": "COMMENTED",
                }
            ),
        )
        logger.info("Got %d from POSTing new(/temp) PR review", response.status_code)
        response = requests.get(reviews_url)

    for i, review in enumerate(reviews):
        if int(review["user"]["id"]) == user_id and review["body"].startswith(
            "<!-- cpp linter action -->"
        ):
            review_id = int(review["id"])
            if i < len(reviews) - 1:
                response = requests.put(
                    f'{reviews_url}/{review["id"]}',
                    headers=API_HEADERS,
                    data=json.dumps({"body": "This outdated comment has been edited."}),
                )
                logger.info(
                    "Got {} from PATCHing review {} by {}".format(
                        response.status_code,
                        review["id"],
                        review["user"]["login"],
                    )
                )

    logger.info(f"   review_id: {review_id}")
    return review_id


def capture_clang_tools_output(version, checks, style):
    """execute and capture all output from clang-tidy and clang-format."""
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
            "--dry-run",
            filename,
        ]
        with open("clang_format_report.txt", "w", encoding="utf-8") as f_out:
            subprocess.run(cmds, stderr=f_out, stdout=f_out)

        # parse format suggestions from clang-format (exported in XML file)
        cmds[2] = "--output-replacements-xml"
        with open("clang_format_output.xml", "w", encoding="utf-8") as f_out:
            subprocess.run(cmds, stderr=f_out, stdout=f_out)
        parse_fmt_advice(filename)

        if os.path.getsize("clang_tidy_report.txt"):
            # get clang-tidy fixes from stout
            parse_tidy_output()
            if Globals.PAYLOAD_TIDY:
                Globals.PAYLOAD_TIDY += "<hr></details>"
            Globals.PAYLOAD_TIDY += f"<details><summary>{filename}</summary><br>\n"
            for fix in GlobalParser.fixits:
                Globals.PAYLOAD_TIDY += repr(fix)
            GlobalParser.fixits.clear()

        if os.path.getsize("clang_format_report.txt"):
            if not Globals.OUTPUT:
                Globals.OUTPUT = "<!-- cpp linter action -->\n"
                Globals.OUTPUT += (
                    "## :scroll: Run `clang-format` on the following files\n"
                )
            Globals.OUTPUT += f"- [ ] {file['filename']}\n"

    if Globals.PAYLOAD_TIDY:
        Globals.OUTPUT += "\n---\n## :speech_balloon: Output from `clang-tidy`\n"
        Globals.OUTPUT += Globals.PAYLOAD_TIDY + "</details>"

    logger.log(9, "OUTPUT is \n" + Globals.OUTPUT)


def post_results(user_id=41898282):
    """POST action's results using REST API."""
    comments_url = ""
    reviews_url = ""
    review_id = 0
    comments_cnt = 0
    comment_id = 0
    if GITHUB_EVENT_NAME == "pull_request":
        comments_url = f"{GITHUB_API_URL}/repos/{GITHUB_REPOSITORY}/"
        reviews_url = comments_url + f'pulls/{Globals.EVENT_PAYLOAD["number"]}/reviews'
        comments_url += f'issues/{Globals.EVENT_PAYLOAD["number"]}/comments'
        comments_cnt = int(Globals.EVENT_PAYLOAD["comments"])
    elif GITHUB_EVENT_NAME == "push":
        comments_url = Globals.FILES_LINK + "/comments"
        comments_cnt = int(Globals.FILES["commit"]["comment_count"])
    logger.info(f"Number of Comments = {comments_cnt}")
    if comments_cnt:
        # 41898282 is the bot's ID (used for all github actions' generic bot)
        comment_id = remove_duplicate_comments(comments_url, user_id)

    if GITHUB_TOKEN is None:
        logger.error("The GITHUB_TOKEN is required!")
        sys.exit(set_exit_code(1))

    payload = json.dumps({"body": Globals.OUTPUT})
    # logger.log(9, "payload body:\n" + json.dumps({"body": Globals.OUTPUT}, indent=2))

    commit_url = f"{GITHUB_API_URL}/repos/{GITHUB_REPOSITORY}"
    if GITHUB_EVENT_NAME == "push":
        commit_url += f"/comments/{comment_id}"
    else:
        commit_url += f"/issues/comments/{comment_id}"
    logger.info("comments_url: " + comments_url)

    response = None
    if reviews_url:
        review_id = dismiss_stale_reviews(reviews_url, user_id)

        if comment_id:
            response = requests.delete(
                commit_url,
                headers=API_HEADERS,
            )
            logger.info(f"Got {response.status_code} from DELETE {comments_url}")

        response = requests.put(
            reviews_url + f"/{review_id}", headers=API_HEADERS, data=payload
        )
        logger.info(f"Got {response.status_code} from PUT review {review_id} update")
    else:
        if comment_id:
            logger.info("  commit_url: " + commit_url)
            response = requests.patch(commit_url, headers=API_HEADERS, data=payload)
        else:
            response = requests.post(comments_url, headers=API_HEADERS, data=payload)

        logger.info(
            "Got %d response from %sing comment",
            response.status_code,
            "PATCH" if comment_id else "POST",
        )


def main():
    """The main script."""

    # parse cli args
    args = cli_arg_parser.parse_args()

    # override log level if this workflow has run more than once
    RUN_NUMBER = os.getenv("GITHUB_RUN_NUMBER", "0")
    logger.setLevel(int(args.verbosity) if int(RUN_NUMBER) > 1 else 8)
    logger.info("processing run number %d", int(RUN_NUMBER))
    # change working directory
    os.chdir(args.repo_root)

    get_list_of_changed_files()
    filter_out_non_source_files(args.extensions)
    verify_files_are_present()
    capture_clang_tools_output(args.version, args.tidy_checks, args.style)
    set_exit_code(0)
    post_results()  # leave param blank to look for the generic github action bot
    # post_results(14963867)  # 14963867 is user id for 2bndy5


if __name__ == "__main__":
    main()
