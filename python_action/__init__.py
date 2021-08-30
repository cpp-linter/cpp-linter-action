

import io
from os import SEEK_SET


class Globals:
    """Global variables for re-use (non-constant)."""

    PAYLOAD_TIDY = ""  #: The accumulated output of clang-tidy (gets appended to OUTPUT)
    OUTPUT = ""  #: The accumulated body of the resulting comment that gets posted.
    FILES_LINK = ""  #: The URL used to fetch the list of changed files.
    FILES = []  #: The reponding payload containing info about changed files.
    EVENT_PAYLOAD = {}  #: The parsed JSON of the event payload.
    DIFF = None

class GlobalParser:
    """Global variables specific to YML/XML parser."""
    fixits = []  #: each element is for 1 file
    advice = []


def get_line_cnt_from_cols(file_path, offset):
    """gets a line count and columns offsaet from a file's absolute offset."""
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
