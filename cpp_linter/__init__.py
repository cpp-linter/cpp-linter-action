"""The Base module of the `cpp_linter` package. This holds the objects shared by
multiple modules."""
import io
import os
import logging

FOUND_RICH_LIB = False
try:
    from rich.logging import RichHandler

    FOUND_RICH_LIB = True

    logging.basicConfig(
        format="%(name)s: %(message)s",
        handlers=[RichHandler(show_time=False)],
    )

except ImportError:
    logging.basicConfig()

#: The logging.Logger object used for outputing data.
logger = logging.getLogger("CPP Linter")
if not FOUND_RICH_LIB:
    logger.debug("rich module not found")

# global constant variables
GITHUB_SHA = os.getenv("GITHUB_SHA", "")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", os.getenv("GIT_REST_API", ""))
API_HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3.text+json",
}


class Globals:
    """Global variables for re-use (non-constant)."""

    PAYLOAD_TIDY = ""
    """The accumulated output of clang-tidy (gets appended to OUTPUT)"""
    OUTPUT = ""
    """The accumulated body of the resulting comment that gets posted."""
    FILES = []
    """The reponding payload containing info about changed files."""
    EVENT_PAYLOAD = {}
    """The parsed JSON of the event payload."""
    response_buffer = None
    """A shared response object for `requests` module."""


class GlobalParser:
    """Global variables specific to output parsers. Each element in each of the
    following attributes represents a clang-tool's output for 1 source file.
    """

    tidy_notes = []
    """This can only be a `list` of type
    [`TidyNotification`][cpp_linter.clang_tidy.TidyNotification]"""
    tidy_advice = []
    """This can only be a `list` of type
    [`YMLFixit`][cpp_linter.clang_tidy_yml.YMLFixit]"""
    format_advice = []
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
    line_cnt = 1
    last_lf_pos = 0
    cols = 1
    file_path = file_path.replace("/", os.sep)
    # logger.debug("Getting line count from %s at offset %d", file_path, offset)
    with io.open(file_path, "rb") as src_file:
        max_len = src_file.seek(0, io.SEEK_END)
        src_file.seek(0, io.SEEK_SET)
        while src_file.tell() != offset and src_file.tell() < max_len:
            char = src_file.read(1)
            if char == b"\n":
                line_cnt += 1
                last_lf_pos = src_file.tell() - 1  # -1 because LF is part of offset
        cols = src_file.tell() - last_lf_pos
    return (line_cnt, cols)


def log_response_msg():
    """Output the response buffer's message on failed request"""
    if Globals.response_buffer.status_code >= 400:
        logger.error("response returned message: %s", Globals.response_buffer.text)
