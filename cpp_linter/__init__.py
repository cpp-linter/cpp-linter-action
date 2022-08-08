"""The Base module of the `cpp_linter` package. This holds the objects shared by
multiple modules."""
import os
from pathlib import Path
import platform
import logging
from typing import TYPE_CHECKING, List, Dict, Union, Any
from requests import Response

if TYPE_CHECKING:  # Used to avoid circular imports
    from cpp_linter.clang_format_xml import XMLFixit
    from cpp_linter.clang_tidy_yml import YMLFixit
    from cpp_linter.clang_tidy import TidyNotification

FOUND_RICH_LIB = False
try:
    from rich.logging import RichHandler

    FOUND_RICH_LIB = True

    logging.basicConfig(
        format="%(name)s: %(message)s",
        handlers=[RichHandler(show_time=False)],
    )

except ImportError:  # pragma: no cover
    logging.basicConfig()

#: The logging.Logger object used for outputting data.
logger = logging.getLogger("CPP Linter")
if not FOUND_RICH_LIB:
    logger.debug("rich module not found")

# global constant variables
IS_ON_RUNNER = bool(os.getenv("CI"))
GITHUB_SHA = os.getenv("GITHUB_SHA", "")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", os.getenv("GIT_REST_API", ""))
API_HEADERS = {
    "Accept": "application/vnd.github.v3.text+json",
}
if GITHUB_TOKEN:
    API_HEADERS["Authorization"] = f"token {GITHUB_TOKEN}"
IS_ON_WINDOWS = platform.system().lower() == "windows"


class Globals:
    """Global variables for re-use (non-constant)."""

    PAYLOAD_TIDY: str = ""
    """The accumulated output of clang-tidy (gets appended to OUTPUT)"""
    OUTPUT: str = ""
    """The accumulated body of the resulting comment that gets posted."""
    FILES: Union[List[Dict[str, Any]], Dict[str, Any]] = []
    """The responding payload containing info about changed files."""
    EVENT_PAYLOAD: Dict[str, Any] = {}
    """The parsed JSON of the event payload."""
    response_buffer = Response()
    """A shared response object for `requests` module."""


class GlobalParser:
    """Global variables specific to output parsers. Each element in each of the
    following attributes represents a clang-tool's output for 1 source file.
    """

    tidy_notes = []  # type: List[TidyNotification]
    """This can only be a `list` of type
    [`TidyNotification`][cpp_linter.clang_tidy.TidyNotification]"""
    tidy_advice = []  # type: List[YMLFixit]
    """This can only be a `list` of type
    [`YMLFixit`][cpp_linter.clang_tidy_yml.YMLFixit]"""
    format_advice = []  # type: List[XMLFixit]
    """This can only be a `list` of type
    [`XMLFixit`][cpp_linter.clang_format_xml.XMLFixit]"""


def get_line_cnt_from_cols(file_path: str, offset: int) -> tuple:
    """Gets a line count and columns offset from a file's absolute offset.

    Args:
        file_path: Path to file.
        offset: The byte offset to translate

    Returns:
        A `tuple` of 2 `int` numbers:

        - Index 0 is the line number for the given offset.
        - Index 1 is the column number for the given offset on the line.
    """
    # logger.debug("Getting line count from %s at offset %d", file_path, offset)
    contents = Path(file_path).read_bytes()[:offset]
    return (contents.count(b"\n") + 1, offset - contents.rfind(b"\n"))


def range_of_changed_lines(
    file_obj: Dict[str, Any], lines_changed_only: int
) -> List[int]:
    """Assemble a list of lines changed.

    Args:
        file_obj: The file's JSON object.
        lines_changed_only: A flag to indicate the focus of certain lines.

            - 0: focuses on all lines in file.
            - 1: focuses on any lines shown in the event's diff
                (may include unchanged lines).
            - 2: focuses strictly on lines in the diff that contain additions.
    Returns:
        A list of line numbers for which to give attention.
    """
    if lines_changed_only:
        ranges = file_obj["line_filter"][
            "diff_chunks" if lines_changed_only == 1 else "lines_added"
        ]
        return [l for r in ranges for l in range(r[0], r[1])]
    return []


def log_response_msg() -> bool:
    """Output the response buffer's message on a failed request.

    Returns:
        A bool describing if response's status code was less than 400.
    """
    if Globals.response_buffer.status_code >= 400:
        logger.error(
            "response returned %d message: %s",
            Globals.response_buffer.status_code,
            Globals.response_buffer.text,
        )
        return False
    return True


def assemble_version_exec(tool_name: str, specified_version: str) -> str:
    """Assembles the command to the executable of the given clang tool based on given
    version information.

    Args:
        tool_name: The name of the clang tool to be executed.
        specified_version: The version number or the installed path to a version of
            the tool's executable.
    """
    suffix = ".exe" if IS_ON_WINDOWS else ""
    if specified_version.isdigit():  # version info is not a path
        # let's assume the exe is in the PATH env var
        if IS_ON_WINDOWS:
            # installs don't usually append version number to exe name on Windows
            return f"{tool_name}{suffix}"  # omit version number
        return f"{tool_name}-{specified_version}{suffix}"
    version_path = Path(specified_version).resolve()  # make absolute
    for path in [
        # if installed via KyleMayes/install-llvm-action using the `directory` option
        version_path / "bin" / (tool_name + suffix),
        # if installed via clang-tools-pip pkg using the `-d` option
        version_path / (tool_name + suffix),
    ]:
        if path.exists():
            return str(path)
    return tool_name + suffix
