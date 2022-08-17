"""Run clang-tidy and clang-format on a list of changed files provided by GitHub's
REST API. If executed from command-line, then [`main()`][cpp_linter.run.main] is
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
from pathlib import Path, PurePath
import os
import sys
import argparse
import configparser
import json
from typing import cast, List, Dict, Any, Tuple
import requests
from . import (
    Globals,
    GlobalParser,
    logging,
    logger,
    GITHUB_TOKEN,
    GITHUB_SHA,
    API_HEADERS,
    IS_ON_RUNNER,
    log_response_msg,
    range_of_changed_lines,
    assemble_version_exec,
)
from .clang_tidy_yml import parse_tidy_suggestions_yml
from .clang_format_xml import parse_format_replacements_xml
from .clang_tidy import parse_tidy_output, TidyNotification
from .thread_comments import remove_bot_comments, list_diff_comments  # , get_review_id


# global constant variables
GITHUB_EVENT_PATH = os.getenv("GITHUB_EVENT_PATH", "")
GITHUB_API_URL = os.getenv("GITHUB_API_URL", "https://api.github.com")
GITHUB_REPOSITORY = os.getenv("GITHUB_REPOSITORY", "")
GITHUB_EVENT_NAME = os.getenv("GITHUB_EVENT_NAME", "unknown")
GITHUB_WORKSPACE = os.getenv("GITHUB_WORKSPACE", "")
IS_USING_DOCKER = os.getenv("USING_CLANG_TOOLS_DOCKER", os.getenv("CLANG_VERSIONS"))
RUNNER_WORKSPACE = "/github/workspace" if IS_USING_DOCKER else GITHUB_WORKSPACE

# setup CLI args
cli_arg_parser = argparse.ArgumentParser(
    description=__doc__[: __doc__.find("If executed from")]
)
cli_arg_parser.add_argument(
    "-v",
    "--verbosity",
    type=int,
    default=10,
    help="The logging level. Defaults to level 20 (aka 'logging.INFO').",
)
cli_arg_parser.add_argument(
    "-p",
    "--database",
    default="",
    help="-p <build-path> is used to read a compile command database."
    "For example, it can be a CMake build directory in which a file named"
    "compile_commands.json exists (use -DCMAKE_EXPORT_COMPILE_COMMANDS=ON"
    "CMake option to get this output). When no build path is specified,"
    "a search for compile_commands.json will be attempted through all"
    "parent paths of the first input file . See:"
    "https://clang.llvm.org/docs/HowToSetupToolingForLLVM.html for an"
    "example of setting up Clang Tooling on a source tree.",
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
    default="",
    help="The desired version of the clang tools to use. Accepted options are strings "
    "which can be 8, 9, 10, 11, 12, 13, 14. Defaults to '%(default)s'. On Windows, "
    "this can also be a path to the install location of LLVM",
)
cli_arg_parser.add_argument(
    "-e",
    "--extensions",
    default=["c", "h", "C", "H", "cpp", "hpp", "cc", "hh", "c++", "h++", "cxx", "hxx"],
    type=lambda i: [ext.strip().lstrip(".") for ext in i.split(",")],
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
    default=".github",
    help="Set this option with paths to ignore. In the case of multiple "
    "paths, you can set this option (multiple times) for each path. This can "
    "also have files, but the file's relative path has to be specified as well "
    "with the filename. Prefix a path with '!' to explicitly not ignore it.",
)
cli_arg_parser.add_argument(
    "-l",
    "--lines-changed-only",
    default=0,
    type=lambda a: 1 if a.lower() == "true" else (2 if a.lower() == "strict" else 0),
    help="Set this option to 'true' to only analyze changes in the event's diff. "
    "Set this to 'strict' to only analyze additions in the event's diff. "
    "Defaults to %(default)s.",
)
cli_arg_parser.add_argument(
    "-f",
    "--files-changed-only",
    default="false",
    type=lambda input: input.lower() == "true",
    help="Set this option to 'false' to analyze any source files in the repo. "
    "Defaults to %(default)s.",
)
cli_arg_parser.add_argument(
    "-t",
    "--thread-comments",
    default="false",
    type=lambda input: input.lower() == "true",
    help="Set this option to false to disable the use of thread comments as feedback."
    "Defaults to %(default)s.",
)
cli_arg_parser.add_argument(
    "-a",
    "--file-annotations",
    default="true",
    type=lambda input: input.lower() == "true",
    help="Set this option to false to disable the use of file annotations as feedback."
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
log_commander = logging.getLogger("LOG COMMANDER")  # create a child of our logger obj
log_commander.setLevel(logging.DEBUG)  # be sure that log commands are output
console_handler = logging.StreamHandler()  # Create special stdout stream handler
console_handler.setFormatter(logging.Formatter("%(message)s"))  # no formatted log cmds
log_commander.addHandler(console_handler)  # Use special handler for log_commander
log_commander.propagate = False


def start_log_group(name: str) -> None:
    """Begin a collapsable group of log statements.

    Args:
        name: The name of the collapsable group
    """
    log_commander.fatal("::group::%s", name)


def end_log_group() -> None:
    """End a collapsable group of log statements."""
    log_commander.fatal("::endgroup::")


def is_file_in_list(paths: List[str], file_name: str, prompt: str) -> bool:
    """Determine if a file is specified in a list of paths and/or filenames.

    Args:
        paths: A list of specified paths to compare with. This list can contain a
            specified file, but the file's path must be included as part of the
            filename.
        file_name: The file's path & name being sought in the `paths` list.
        prompt: A debugging prompt to use when the path is found in the list.
    Returns:
        - True if `file_name` is in the `paths` list.
        - False if `file_name` is not in the `paths` list.
    """
    for path in paths:
        result = os.path.commonpath(
            [PurePath(path).as_posix(), PurePath(file_name).as_posix()]
        )
        if result == path:
            logger.debug(
                '"./%s" is %s as specified in the domain "./%s"',
                file_name,
                prompt,
                path,
            )
            return True
    return False


def get_list_of_changed_files() -> None:
    """Fetch the JSON payload of the event's changed files. Sets the
    [`FILES`][cpp_linter.Globals.FILES] attribute."""
    start_log_group("Get list of specified source files")
    files_link = f"{GITHUB_API_URL}/repos/{GITHUB_REPOSITORY}/"
    if GITHUB_EVENT_NAME == "pull_request":
        files_link += f"pulls/{Globals.EVENT_PAYLOAD['number']}/files"
    else:
        if GITHUB_EVENT_NAME != "push":
            logger.warning(
                "Triggered on unsupported event '%s'. Behaving like a push event.",
                GITHUB_EVENT_NAME,
            )
        files_link += f"commits/{GITHUB_SHA}"
    logger.info("Fetching files list from url: %s", files_link)
    Globals.response_buffer = requests.get(files_link, headers=API_HEADERS)
    log_response_msg()
    if GITHUB_EVENT_NAME == "pull_request":
        Globals.FILES = Globals.response_buffer.json()
    else:
        Globals.FILES = Globals.response_buffer.json()["files"]


def consolidate_list_to_ranges(just_numbers: List[int]) -> List[List[int]]:
    """A helper function to [`filter_out_non_source_files()`] that is only used when
    extracting the lines from a diff that contain additions."""
    result: List[List[int]] = []
    for i, n in enumerate(just_numbers):
        if not i:
            result.append([n])
        elif n - 1 != just_numbers[i - 1]:
            result[-1].append(just_numbers[i - 1] + 1)
            result.append([n])
        if i == len(just_numbers) - 1:
            result[-1].append(n + 1)
    return result


def filter_out_non_source_files(
    ext_list: List[str],
    ignored: List[str],
    not_ignored: List[str],
) -> bool:
    """Exclude undesired files (specified by user input 'extensions'). This filter
    applies to the event's [`FILES`][cpp_linter.Globals.FILES] attribute.

    Args:
        ext_list: A list of file extensions that are to be examined.
        ignored: A list of paths to explicitly ignore.
        not_ignored: A list of paths to explicitly not ignore.

    Returns:
        True if there are files to check. False will invoke a early exit (in
        [`main()`][cpp_linter.run.main]) when no files to be checked.
    """
    files = []
    for file in Globals.FILES:
        if (
            PurePath(file["filename"]).suffix.lstrip(".") in ext_list
            and not file["status"].endswith("removed")
            and (
                not is_file_in_list(ignored, file["filename"], "ignored")
                or is_file_in_list(not_ignored, file["filename"], "not ignored")
            )
        ):
            if "patch" in file.keys():
                # get diff details for the file's changes
                # ranges is a list of start/end line numbers shown in the diff
                ranges: List[List[int]] = []
                # additions is a list line numbers in the diff containing additions
                additions: List[int] = []
                line_numb_in_diff: int = 0
                for line in cast(str, file["patch"]).splitlines():
                    if line.startswith("+"):
                        additions.append(line_numb_in_diff)
                    if line.startswith("@@ -"):
                        hunk = line[line.find(" +") + 2 : line.find(" @@")].split(",")
                        start_line, hunk_length = [int(x) for x in hunk]
                        ranges.append([start_line, hunk_length + start_line])
                        line_numb_in_diff = start_line
                    elif not line.startswith("-"):
                        line_numb_in_diff += 1
                file["line_filter"] = dict(
                    diff_chunks=ranges,
                    lines_added=consolidate_list_to_ranges(additions),
                )
            files.append(file)

    if files:
        logger.info(
            "Giving attention to the following files:\n\t%s",
            "\n\t".join([f["filename"] for f in files]),
        )
        Globals.FILES = files
        if not IS_ON_RUNNER:  # if not executed on a github runner
            # dump altered json of changed files
            Path(".changed_files.json").write_text(
                json.dumps(Globals.FILES, indent=2),
                encoding="utf-8",
            )
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
    for file in Globals.FILES:
        file_name = Path(file["filename"])
        if not file_name.exists():
            logger.warning("Could not find %s! Did you checkout the repo?", file_name)
            logger.info("Downloading file from url: %s", file["raw_url"])
            Globals.response_buffer = requests.get(file["raw_url"])
            # retain the repo's original structure
            Path.mkdir(file_name.parent, parents=True, exist_ok=True)
            file_name.write_text(Globals.response_buffer.text, encoding="utf-8")


def list_source_files(
    ext_list: List[str], ignored_paths: List[str], not_ignored: List[str]
) -> bool:
    """Make a list of source files to be checked. The resulting list is stored in
    [`FILES`][cpp_linter.Globals.FILES].

    Args:
        ext_list: A list of file extensions that should by attended.
        ignored_paths: A list of paths to explicitly ignore.
        not_ignored: A list of paths to explicitly not ignore.

    Returns:
        True if there are files to check. False will invoke a early exit (in
        [`main()`][cpp_linter.run.main]) when no files to be checked.
    """
    start_log_group("Get list of specified source files")

    root_path = Path(".")
    for ext in ext_list:
        for rel_path in root_path.rglob(f"*.{ext}"):
            for parent in rel_path.parts[:-1]:
                if parent.startswith("."):
                    break
            else:
                file_path = rel_path.as_posix()
                logger.debug('"./%s" is a source code file', file_path)
                if not is_file_in_list(
                    ignored_paths, file_path, "ignored"
                ) or is_file_in_list(not_ignored, file_path, "not ignored"):
                    Globals.FILES.append(dict(filename=file_path))

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
    filename: str,
    file_obj: Dict[str, Any],
    version: str,
    checks: str,
    lines_changed_only: int,
    database: str,
    repo_root: str,
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
    if checks == "-*":  # if all checks are disabled, then clang-tidy is skipped
        # clear the clang-tidy output file and exit function
        Path("clang_tidy_report.txt").write_bytes(b"")
        return
    filename = PurePath(filename).as_posix()
    cmds = [
        assemble_version_exec("clang-tidy", version),
        "--export-fixes=clang_tidy_output.yml",
    ]
    if checks:
        cmds.append(f"-checks={checks}")
    if database:
        cmds.append("-p")
        if not PurePath(database).is_absolute():
            database = str(Path(RUNNER_WORKSPACE, repo_root, database).resolve())
        cmds.append(database)
    if lines_changed_only:
        ranges = "diff_chunks" if lines_changed_only == 1 else "lines_added"
        line_ranges = dict(name=filename, lines=file_obj["line_filter"][ranges])
        logger.info("line_filter = %s", json.dumps([line_ranges]))
        cmds.append(f"--line-filter={json.dumps([line_ranges])}")
    cmds.append(filename)
    # clear yml file's content before running clang-tidy
    Path("clang_tidy_output.yml").write_bytes(b"")
    logger.info('Running "%s"', " ".join(cmds))
    results = subprocess.run(cmds, capture_output=True)
    Path("clang_tidy_report.txt").write_bytes(results.stdout)
    logger.debug("Output from clang-tidy:\n%s", results.stdout.decode())
    if Path("clang_tidy_output.yml").stat().st_size:
        parse_tidy_suggestions_yml()  # get clang-tidy fixes from yml
    if results.stderr:
        logger.debug(
            "clang-tidy made the following summary:\n%s", results.stderr.decode()
        )


def run_clang_format(
    filename: str,
    file_obj: Dict[str, Any],
    version: str,
    style: str,
    lines_changed_only: int,
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
    if not style:  # if `style` == ""
        Path("clang_format_output.xml").write_bytes(b"")
        return  # clear any previous output and exit
    cmds = [
        assemble_version_exec("clang-format", version),
        f"-style={style}",
        "--output-replacements-xml",
    ]
    if lines_changed_only:
        ranges = "diff_chunks" if lines_changed_only == 1 else "lines_added"
        for line_range in file_obj["line_filter"][ranges]:
            cmds.append(f"--lines={line_range[0]}:{line_range[1]}")
    cmds.append(PurePath(filename).as_posix())
    logger.info('Running "%s"', " ".join(cmds))
    results = subprocess.run(cmds, capture_output=True)
    Path("clang_format_output.xml").write_bytes(results.stdout)
    if results.returncode:
        logger.debug(
            "%s raised the following error(s):\n%s", cmds[0], results.stderr.decode()
        )


def create_comment_body(
    filename: str,
    file_obj: Dict[str, Any],
    lines_changed_only: int,
    tidy_notes: List[TidyNotification],
):
    """Create the content for a thread comment about a certain file.
    This is a helper function to [`capture_clang_tools_output()`].

    Args:
        filename: The file's name (& path).
        file_obj: The file's JSON `dict`.
        lines_changed_only: A flag used to filter the comment based on line changes.
        tidy_notes: A list of cached notifications from clang-tidy. This is used to
            avoid duplicated content in comment, and it is later used again by
            [`make_annotations()`] after [`capture_clang_tools_output()`] us finished.
    """
    ranges = range_of_changed_lines(file_obj, lines_changed_only)
    if Path("clang_tidy_report.txt").stat().st_size:
        parse_tidy_output()  # get clang-tidy fixes from stdout
        comment_output = ""
        if Globals.PAYLOAD_TIDY:
            Globals.PAYLOAD_TIDY += "<hr></details>"
        for fix in GlobalParser.tidy_notes:
            if lines_changed_only and fix.line not in ranges:
                continue
            comment_output += repr(fix)
            tidy_notes.append(fix)
        if comment_output:
            Globals.PAYLOAD_TIDY += f"<details><summary>{filename}</summary><br>\n"
            Globals.PAYLOAD_TIDY += comment_output
        GlobalParser.tidy_notes.clear()  # empty list to avoid duplicated output

    if Path("clang_format_output.xml").stat().st_size:
        parse_format_replacements_xml(PurePath(filename).as_posix())
        if GlobalParser.format_advice and GlobalParser.format_advice[-1].replaced_lines:
            should_comment = lines_changed_only == 0
            if not should_comment:
                for line in [
                    replacement.line
                    for replacement in GlobalParser.format_advice[-1].replaced_lines
                ]:
                    if line in ranges:
                        should_comment = True
                        break
            if should_comment:
                if not Globals.OUTPUT:
                    Globals.OUTPUT = "<!-- cpp linter action -->\n## :scroll: "
                    Globals.OUTPUT += "Run `clang-format` on the following files\n"
                Globals.OUTPUT += f"- [ ] {file_obj['filename']}\n"


def capture_clang_tools_output(
    version: str,
    checks: str,
    style: str,
    lines_changed_only: int,
    database: str,
    repo_root: str,
):
    """Execute and capture all output from clang-tidy and clang-format. This aggregates
    results in the [`OUTPUT`][cpp_linter.Globals.OUTPUT].

    Args:
        version: The version of clang-tidy to run.
        checks: The `str` of comma-separated regulate expressions that describe
            the desired clang-tidy checks to be enabled/configured.
        style: The clang-format style rules to adhere. Set this to 'file' to
            use the relative-most .clang-format configuration file.
        lines_changed_only: A flag that forces focus on only changes in the event's
            diff info.
    """
    # temporary cache of parsed notifications for use in log commands
    tidy_notes: List[TidyNotification] = []
    for file in Globals.FILES:
        filename = cast(str, file["filename"])
        start_log_group(f"Performing checkup on {filename}")
        run_clang_tidy(
            filename, file, version, checks, lines_changed_only, database, repo_root
        )
        run_clang_format(filename, file, version, style, lines_changed_only)
        end_log_group()

        create_comment_body(filename, file, lines_changed_only, tidy_notes)

    if Globals.PAYLOAD_TIDY:
        if not Globals.OUTPUT:
            Globals.OUTPUT = "<!-- cpp linter action -->\n"
        else:
            Globals.OUTPUT += "\n---\n"
        Globals.OUTPUT += "## :speech_balloon: Output from `clang-tidy`\n"
        Globals.OUTPUT += Globals.PAYLOAD_TIDY
    GlobalParser.tidy_notes = tidy_notes[:]  # restore cache of notifications


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
    payload = list_diff_comments(2)  # only focus on additions in diff
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
                and comment["path"] == body["path"]
            ):
                already_posted = True
                if comment["body"] != body["body"]:
                    comment_id = str(comment["id"])  # use this to update comment
                else:
                    break
        if already_posted and comment_id is None:
            logger.info("comment %d already posted", i)
            continue  # don't bother re-posting the same comment

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


def make_annotations(
    style: str, file_annotations: bool, lines_changed_only: int
) -> bool:
    """Use github log commands to make annotations from clang-format and
    clang-tidy output.

    Args:
        style: The chosen code style guidelines. The value 'file' is replaced with
            'custom style'.
    """
    count = 0
    files = (
        Globals.FILES
        if GITHUB_EVENT_NAME == "pull_request" or isinstance(Globals.FILES, list)
        else cast(Dict[str, Any], Globals.FILES)["files"]
    )
    for advice, file in zip(GlobalParser.format_advice, files):
        line_filter = range_of_changed_lines(file, lines_changed_only)
        if advice.replaced_lines:
            if file_annotations:
                output = advice.log_command(style, line_filter)
                if output is not None:
                    log_commander.info(output)
                    count += 1
    for note in GlobalParser.tidy_notes:
        if lines_changed_only:
            filename = note.filename.replace("\\", "/")
            line_filter = []
            for file in files:
                if filename == file["filename"]:
                    line_filter = range_of_changed_lines(file, lines_changed_only)
                    break
            else:
                continue
            if note.line in line_filter:
                count += 1
                log_commander.info(note.log_command())
        else:
            count += 1
            log_commander.info(note.log_command())
    logger.info("Created %d annotations", count)
    return bool(count)


def parse_ignore_option(paths: str) -> Tuple[List[str], List[str]]:
    """Parse a given string of paths (separated by a '|') into `ignored` and
    `not_ignored` lists of strings.

    Args:
        paths: This argument conforms to the CLI arg `--ignore` (or `-i`).

    Returns: Returns a tuple of lists in which each list is a set of strings.
        index 0 is the `ignored` list
        index 1 is the `not_ignored` list
    """
    ignored, not_ignored = ([], [])

    for path in paths.split("|"):
        is_included = path.startswith("!")
        if path.startswith("!./" if is_included else "./"):
            path = path.replace("./", "", 1)  # relative dir is assumed
        path = path.strip()  # strip leading/trailing spaces
        if is_included:
            not_ignored.append(path[1:])  # strip leading `!`
        else:
            ignored.append(path)

    # auto detect submodules
    gitmodules = Path(".gitmodules")
    if gitmodules.exists():
        submodules = configparser.ConfigParser()
        submodules.read(gitmodules.resolve().as_posix())
        for module in submodules.sections():
            path = submodules[module]["path"]
            if path not in not_ignored:
                logger.info("Appending submodule to ignored paths: %s", path)
                ignored.append(path)

    if ignored:
        logger.info(
            "Ignoring the following paths/files:\n\t./%s",
            "\n\t./".join(f for f in ignored),
        )
    if not_ignored:
        logger.info(
            "Not ignoring the following paths/files:\n\t./%s",
            "\n\t./".join(f for f in not_ignored),
        )
    return (ignored, not_ignored)


def main():
    """The main script."""

    # The parsed CLI args
    args = cli_arg_parser.parse_args()

    #  force files-changed-only to reflect value of lines-changed-only
    if args.lines_changed_only:
        args.files_changed_only = True

    # set logging verbosity
    logger.setLevel(int(args.verbosity))

    # prepare ignored paths list
    ignored, not_ignored = parse_ignore_option(args.ignore)

    logger.info("processing %s event", GITHUB_EVENT_NAME)

    # change working directory
    os.chdir(args.repo_root)

    if GITHUB_EVENT_PATH:
        # load event's json info about the workflow run
        Globals.EVENT_PAYLOAD = json.loads(
            Path(GITHUB_EVENT_PATH).read_text(encoding="utf-8")
        )
    if logger.getEffectiveLevel() <= logging.DEBUG:
        start_log_group("Event json from the runner")
        logger.debug(json.dumps(Globals.EVENT_PAYLOAD))
        end_log_group()

    exit_early = False
    if args.files_changed_only:
        get_list_of_changed_files()
        exit_early = not filter_out_non_source_files(
            args.extensions,
            ignored,
            not_ignored,
        )
        if not exit_early:
            verify_files_are_present()
    else:
        exit_early = not list_source_files(args.extensions, ignored, not_ignored)
    end_log_group()
    if exit_early:
        sys.exit(set_exit_code(0))

    capture_clang_tools_output(
        args.version,
        args.tidy_checks,
        args.style,
        args.lines_changed_only,
        args.database,
        args.repo_root,
    )

    start_log_group("Posting comment(s)")
    thread_comments_allowed = True
    if GITHUB_EVENT_PATH and "private" in Globals.EVENT_PAYLOAD["repository"]:
        thread_comments_allowed = (
            Globals.EVENT_PAYLOAD["repository"]["private"] is not True
        )
    if args.thread_comments and thread_comments_allowed:
        post_results(False)  # False is hard-coded to disable diff comments.
    set_exit_code(
        int(
            make_annotations(args.style, args.file_annotations, args.lines_changed_only)
        )
    )
    end_log_group()


if __name__ == "__main__":
    main()
