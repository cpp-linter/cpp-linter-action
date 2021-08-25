"""parse output from clang-tidy and clang-format"""
import os
import re

# import json


CWD_HEADER_GAURD = bytes(
    os.getcwd().upper().replace("/", "_").replace("-", "_"), encoding="utf-8"
)


class TidyDiagnostic:
    """Create an object that represents a diagnostic output found in the
    YAML exported from clang-tidy"""

    def __init__(self, diagnostic_name):
        self.name = diagnostic_name
        self.message = ""
        self.line = 0
        self.offset = 0
        self.replacements = []


class TidyReplacement:
    """Create an object representing a clang-tidy suggested replacement"""

    def __init__(self):
        self.offset = 0
        self.length = 0
        self.text = b""


def get_line_cnt_from_offset(file_path, offset):
    """gets a line count and columns offsaet from a file's absolute offset."""
    line_cnt = 1
    last_lf_pos = 0
    with open(file_path, "r", encoding="utf-8") as src_file:
        while src_file.tell() != offset:
            # print("file_pos =", src_file.tell())
            char = src_file.read(1)
            if char == "\n":
                line_cnt += 1
                # -1 because LF is part of offset
                last_lf_pos = src_file.tell() - 1
        cols = src_file.tell() - last_lf_pos
    return (line_cnt, cols)


def parse_tidy_yml():
    """Read a YAML file from clang-tidy and create a list of suggestions from it."""
    diag_results = []
    curr_replacement = None
    in_replacement_text = False
    file_path = ""
    with open("clang_tidy_output.yml", "r", encoding="utf-8") as yml_file:
        for line in yml_file.readlines():
            if not in_replacement_text:
                line_striped = line.lstrip()
                if line_striped.startswith("MainSourceFile:"):
                    file_path = (
                        line_striped[len("MainSourceFile:") :].strip().strip("'")
                    )
                    print("file path =", file_path)
                    # if src_file is not None:
                    #     src_file.close()
                    # src_file = open(file_path, "r", encoding="utf-8")
                if line_striped.startswith("- DiagnosticName:"):
                    diag_results.append(TidyDiagnostic(line_striped[17:].strip()))
                elif line_striped.startswith("Message:"):
                    msg = line_striped[len("Message:") :].lstrip()
                    has_enclosed_quotes = msg[0] == "'" and msg[-2] == "'"
                    msg = msg[:-1] if not has_enclosed_quotes else msg[1:-2]
                    msg = msg.replace("''", '"')
                    diag_results[len(diag_results) - 1].message = msg
                elif line_striped.startswith("FileOffset:"):
                    offset = int(line_striped[len("FileOffset:") :].strip())
                    (
                        diag_results[len(diag_results) - 1].line,
                        diag_results[len(diag_results) - 1].offset,
                    ) = get_line_cnt_from_offset(file_path, offset)
                elif line_striped.startswith("Offset:"):
                    # start a new replacement obj
                    curr_replacement = TidyReplacement()
                    offset = int(line_striped[len("Offset:") :].strip())
                    (
                        curr_replacement.line,
                        curr_replacement.offset,
                    ) = get_line_cnt_from_offset(file_path, offset)
                elif line_striped.startswith("Length:"):
                    curr_replacement.length = int(
                        line_striped[len("Length:") :].strip()
                    )
                elif line_striped.startswith("ReplacementText:"):
                    text = (
                        line_striped[len("ReplacementText:") :]
                        .lstrip()[1:]
                        .encode("utf-8")
                    )
                    in_replacement_text = not text.endswith(b"'\n")
                    curr_replacement.text = text[: -1 - (not in_replacement_text)]
                    if not in_replacement_text:
                        diag_results[len(diag_results) - 1].replacements.append(
                            curr_replacement
                        )
            else:
                if line.endswith("'\n"):
                    in_replacement_text = False
                    curr_replacement.text += line[:-2].encode("utf-8")
                    diag_results[len(diag_results) - 1].replacements.append(
                        curr_replacement
                    )
                else:
                    curr_replacement.text += line.encode("utf-8")
    # print results
    for i, diag in enumerate(diag_results):
        # filter out absolute header gaurds
        if diag.message.startswith("header is missing header guard"):
            print("filtering header guard suggestion (making relative to repo root)")
            diag_results[i].replacements[0].text = diag.replacements[0].text.replace(
                CWD_HEADER_GAURD, b""
            )
        print(
            f"diagnostic name: {diag.name}\n    message: {diag.message}\n"
            f"    @ line {diag.line} offset: {diag.offset}"
        )
        for replac in diag_results[i].replacements:
            print(
                f"    replace @ line {replac.line} offset {replac.offset} "
                f"for length {replac.length} of original\n"
                f"\treplace text: {replac.text}"
            )


class TidyNotification:
    """Create a object that decodes info from the clang-tidy output's initial line that
    details a specific notification."""

    def __init__(self, notification_line):
        (
            self.filename,
            self.line_number,
            self.line_columns,
            self.note_type,
            self.note_info,
        ) = notification_line.split(":")
        self.diagnostic = re.search("\[.*\]", self.note_info).group(0)
        self.note_info = self.note_info.replace(self.diagnostic, "").strip()
        self.note_type = self.note_type.strip()
        self.diagnostic = self.diagnostic[1:-2]
        self.line_number = int(self.line_number)
        self.line_columns = int(self.line_columns)
        self.filename = self.filename.replace(os.getcwd() + os.sep, "")
        self.fixit_lines = []

    def __repr__(self) -> str:
        return (
            f"{self.filename}:{self.line_number}:{self.line_columns}:"
            f" {self.note_type}: {self.note_info} [{self.diagnostic}]"
        )


def parse_tidy_output():
    """Parse clang-tidy output in a file created from stdout"""
    tidy_notifications = []
    with open("clang_tidy_output.txt", "r", encoding="utf-8") as tidy_out:
        for line in tidy_out.readlines():
            if re.search("^.*:\d+:\d+:\s\w+:.*\[.*\]$", line) is not None:
                tidy_notifications.append(TidyNotification(line))
            else:
                if tidy_notifications:
                    tidy_notifications[len(tidy_notifications) - 1].fixit_lines.append(
                        line
                    )
    for notification in tidy_notifications:
        print(repr(notification))
        print("".join(notification.fixit_lines))


if __name__ == "__main__":
    # parse_tidy_output()
    parse_tidy_yml()
