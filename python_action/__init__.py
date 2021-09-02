"""The Base module of the `python_action` package. This holds the objects shared by
multiple modules."""
import io
from os import SEEK_SET


class Globals:
    """Global variables for re-use (non-constant)."""

    PAYLOAD_TIDY = ""
    """The accumulated output of clang-tidy (gets appended to OUTPUT)"""
    OUTPUT = ""
    """The accumulated body of the resulting comment that gets posted."""
    FILES_LINK = ""
    """The URL used to fetch the list of changed files."""
    FILES = []
    """The reponding payload containing info about changed files."""
    EVENT_PAYLOAD = {}
    """The parsed JSON of the event payload."""
    DIFF = None
    """The unified diff for the event. This will be a `unidiff.PatchSet`
    (`list`) of `unidiff.PatchedFile` objects. Each `unidiff.PatchedFile`
    object is a `list` of hunks."""
    response_buffer = None
    """A shared response object for `requests` module."""

class GlobalParser:
    """Global variables specific to output parsers. Each element in each of the
    following attributes represents a clang-tool's output for 1 source file.

    """
    tidy_notes = []
    """This can only be a `list` of type [`TidyNotification`][python_action.clang_tidy.TidyNotification]"""
    tidy_advice = []
    """This can only be a `list` of type [`YMLFixin`][python_action.clang_tidy_yml.YMLFixin]"""
    format_advice = []
    """This can only be a `list` of type [`XMLFixin`][python_action.clang_format_xml.XMLFixin]"""


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
    with io.open(file_path, "r", encoding="utf-8", newline="\n") as src_file:
        src_file.seek(0, io.SEEK_END)
        max_len = src_file.tell()
        src_file.seek(0, io.SEEK_SET)
        while src_file.tell() != offset and src_file.tell() < max_len:
            char = src_file.read(1)
            if char == "\n":
                line_cnt += 1
                last_lf_pos = src_file.tell() - 1  # -1 because LF is part of offset
                if last_lf_pos + 1 > max_len:
                    src_file.newlines = "\r\n"
                    src_file.seek(0, io.SEEK_SET)
                    line_cnt = 1
        cols = src_file.tell() - last_lf_pos
        src_file.newlines
    return (line_cnt, cols)
