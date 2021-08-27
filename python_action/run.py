"""Run clang-tidy and clang-format on a list of changed files provided by GitHub's
REST API."""
import subprocess
import os
import sys
import re
import logging
import argparse
import json
import requests

# global constant variables
GITHUB_EVEN_PATH = os.getenv("GITHUB_EVENT_PATH", "event_payload.json")
GITHUB_API_URL = os.getenv("GITHUB_API_URL", "https://api.github.com")
GITHUB_REPOSITORY = os.getenv("GITHUB_REPOSITORY", "2bndy5/cpp-linter-action")
GITHUB_SHA = os.getenv("GITHUB_SHA", "ed98bc095b286c3f29f9a27d423ad5eb13040ebc")
GITHUB_EVENT_NAME = os.getenv("GITHUB_EVENT_NAME", "pull_request")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", os.getenv("GIT_REST_API", None))
FENCES = "\n```\n"
FILES_LIST_JSON = ".cpp_linter_action_changed_files.json"

# setup logger
logging.basicConfig()
Logger = logging.getLogger("CPP LINTER")

# setup CLI args
cli_arg_parser = argparse.ArgumentParser(description=__doc__)

cli_arg_parser.add_argument(
    "--verbosity",
    default="20",
    help="The logging level. Defaults to level 20 (aka 'logging.INFO')."
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


class Globals:
    """Global variables for re-use (non-constant)."""

    PAYLOAD_TIDY = ""  #: The accumulated output of clang-tidy (gets appended to OUTPUT)
    OUTPUT = ""  #: The accumulated body of the resulting comment that gets posted.
    FILES_LINK = ""  #: The URL used to fetch the list of changed files.
    FILES = []  #: The reponding payload containing info about changed files.
    EVENT_PAYLOAD = {}  #: The parsed JSON of the event payload.


def set_exit_code(override=None):
    """Set the action's exit code."""
    exit_code = override if override is not None else bool(Globals.PAYLOAD_TIDY)
    print(f"::set-output name=checks-failed::{exit_code}")
    return exit_code


def get_list_of_changed_files():
    """Fetch the JSON payload of the event's changed files."""
    Logger.info(f"processing {GITHUB_EVENT_NAME} event")
    with open(GITHUB_EVEN_PATH, "r", encoding="utf-8") as payload:
        Globals.EVENT_PAYLOAD = json.load(payload)

    Globals.FILES_LINK = f"{GITHUB_API_URL}/repos/{GITHUB_REPOSITORY}/"
    if GITHUB_EVENT_NAME == "pull_request":
        Globals.FILES_LINK += f"pulls/{Globals.EVENT_PAYLOAD['number']}/files"
    elif GITHUB_EVENT_NAME == "push":
        Globals.FILES_LINK += f"commits/{GITHUB_SHA}"
    else:
        Logger.warn("triggered on unsupported event.")
        sys.exit(set_exit_code(0))
    Logger.info("Fetching files list from %s", Globals.FILES_LINK)
    Globals.FILES = requests.get(Globals.FILES_LINK).json()
    Logger.debug("files json:\n%s", json.dumps(Globals.FILES, indent=2))


def filter_out_non_source_files(ext_list):
    """exclude undesired files (specified by user input 'extensions')"""
    ext_list = ext_list.split(",")
    files = []
    for file in (
        Globals.FILES if GITHUB_EVENT_NAME == "pull_request" else Globals.FILES["files"]
    ):
        # print(file)
        extension = re.search("\.\w+$", file["filename"])
        if extension is not None and extension.group(0)[1:] in ext_list:
            files.append(file)
    if not files:
        # exit early if no changed files are source files
        Logger.info("No source files need checking!")
        sys.exit(set_exit_code(0))
    else:
        if GITHUB_EVENT_NAME == "pull_request":
            Globals.FILES = files
        else:
            Globals.FILES["files"] = files
        with open(FILES_LIST_JSON, "w", encoding="utf-8") as temp:
            json.dump(Globals.FILES, temp)
    Logger.info("File names: %s", " ".join([f["filename"] for f in files]))


def verify_files_are_present():
    """Download the files if not present. This function assumes the working directory
    is the root of the invoking repository."""
    for file in (
        Globals.FILES if GITHUB_EVENT_NAME == "pull_request" else Globals.FILES["files"]
    ):
        if not os.path.exists(file["filename"]):
            Logger.info("Downloading file %s", file["raw_url"])
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
                    headers={
                        "Authorization": f"token {GITHUB_TOKEN}",
                        "Accept": "application/vnd.github.v3.text+json",
                    },
                )
                Logger.info(f"Got {response.status_code} from DELETE {comment['url']}")
        Logger.debug(
            f'comment id {comment["id"]} from user {comment["user"]["login"]}'
            f' ({comment["user"]["id"]})'
        )
    # print("Comments:", comments)
    with open("comments.json", "w", encoding="utf-8") as json_comments:
        json.dump(comments, json_comments, indent=4)
    return first_comment_id


def capture_clang_tools_output(version, checks, style):
    """execute and capture all output from clang-tidy and clang-format."""
    for file in (
        Globals.FILES if GITHUB_EVENT_NAME == "pull_request" else Globals.FILES["files"]
    ):
        filename = file["filename"]
        if not os.path.exists(file["filename"]):
            filename = os.path.split(file["raw_url"])[1]
        Logger.info("Performing checkup on %s", filename)

        # run clang-tidy
        cmds = [f"clang-tidy-{version}"]
        if checks:
            cmds.append(f"-checks={checks}")
        cmds.append(filename)
        with open("clang_tidy_report.txt", "w", encoding="utf-8") as f_out:
            subprocess.run(cmds, stdout=f_out)

        # run clang-format
        cmds = [
            f"clang-format-{version}",
            f"-style={style}",
            "--dry-run",
            filename,
        ]
        with open("clang_format_report.txt", "w", encoding="utf-8")as f_out:
            subprocess.run(cmds, stderr=f_out, stdout=f_out)

        if os.path.getsize("clang_tidy_report.txt"):
            Globals.PAYLOAD_TIDY += f"### {file['filename']}" + FENCES
            subprocess.run(
                ["sed", "-i", f"s|{os.getcwd()}/||g", "clang_tidy_report.txt"]
            )
            with open("clang_tidy_report.txt", "r", encoding="utf-8") as report:
                for line in report.readlines():
                    Globals.PAYLOAD_TIDY += line
            Globals.PAYLOAD_TIDY += FENCES
        if os.path.getsize("clang_format_report.txt"):
            if not Globals.OUTPUT:
                Globals.OUTPUT = "<!-- cpp linter action -->\n"
                Globals.OUTPUT += "## Run `clang-format` on the following files\n"
            Globals.OUTPUT += f"- [ ] {file['filename']}\n"

    if Globals.PAYLOAD_TIDY:
        Globals.OUTPUT += "\n---\n## Output from `clang-tidy`\n"
        Globals.OUTPUT += Globals.PAYLOAD_TIDY

    Logger.debug("OUTPUT is \n%s", Globals.OUTPUT)


def post_results():
    """POST action's results using REST API."""
    comments_url = ""
    comments_cnt = 0
    comment_id = 0
    if GITHUB_EVENT_NAME == "pull_request":
        comments_url = f"{GITHUB_API_URL}/repos/{GITHUB_REPOSITORY}/"
        comments_url += f'issues/{Globals.EVENT_PAYLOAD["number"]}/comments'
        comments_cnt = int(Globals.EVENT_PAYLOAD["comments"])
    elif GITHUB_EVENT_NAME == "push":
        comments_url = Globals.FILES_LINK + "/comments"
        comments_cnt = int(Globals.FILES["commit"]["comment_count"])
    Logger.info("Number of Comments = %d", comments_cnt)
    if comments_cnt:
        # 41898282 is the bot's ID (used for all github actions' generic bot)
        comment_id = remove_duplicate_comments(comments_url, 41898282)

    if GITHUB_TOKEN is None:
        Logger.error("The GITHUB_TOKEN is required!")
        sys.exit(set_exit_code(1))

    payload = json.dumps({"body": Globals.OUTPUT})
    # print(json.dumps({"body": Globals.OUTPUT}, indent=2))

    commit_url = f"{GITHUB_API_URL}/repos/{GITHUB_REPOSITORY}/comments/{comment_id}"
    headers={
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3.text+json",
        # "Accept": "application/vnd.github.v3.diff",
    }
    # print("type: ", type(headers), headers)
    Logger.info("comments_url: %s", comments_url)
    response = None
    if comment_id:
        Logger.debug("commit_url = %s", commit_url)
        response = requests.patch(commit_url, headers=headers, data=payload)
    else:
        response = requests.post(comments_url, headers=headers, data=payload)
    Logger.info(
        "Got %d response from %sing comment",
        response.status_code,
        "PATCH" if comment_id else "POST"
        )


def main():
    """The main script."""

    args = cli_arg_parser.parse_args()
    Logger.setLevel(int(args.verbosity))

    os.chdir(args.repo_root)
    get_list_of_changed_files()
    filter_out_non_source_files(args.extensions)
    verify_files_are_present()
    capture_clang_tools_output(args.version, args.tidy_checks, args.style)
    set_exit_code(0)
    post_results()


if __name__ == "__main__":
    main()
