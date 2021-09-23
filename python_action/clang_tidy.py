"""Parse output from clang-tidy's stdout"""
import os
import sys
import re
from . import GlobalParser


class TidyNotification:
    """Create a object that decodes info from the clang-tidy output's initial line that
    details a specific notification.

    Attributes:
        diagnostic (str): The clang-tidy check that enabled the notification.
        filename (str): The source filename concerning the notification.
        line (int): The line number of the source file.
        cols (int): The columns of the line that triggered the notification.
        note_type (str): The priority level of notification (warning/error).
        note_info (str): The rationale of the notification.
        fixit_lines (list): A `list` of lines (`str`) for the code-block in the notification.
    """

    def __init__(self, notification_line: str):
        """
        Args:
            notification_line: The first line in the notification.
        """
        sliced_line = notification_line.split(":")
        if sys.platform.startswith("win32") and len(sliced_line) > 5:
            # sliced_list items 0 & 1 are the path seperated at the ":".
            # we need to re-assemble the path for correct list expansion (see below)
            sliced_line = [sliced_line[0] + ":" + sliced_line[1]] + sliced_line[2:]
        (
            self.filename,
            self.line,
            self.cols,
            self.note_type,
            self.note_info,
        ) = sliced_line

        self.diagnostic = re.search("\[.*\]", self.note_info).group(0)
        self.note_info = self.note_info.replace(self.diagnostic, "").strip()
        self.diagnostic = self.diagnostic[1:-1]
        self.note_type = self.note_type.strip()
        self.line = int(self.line)
        self.cols = int(self.cols)
        self.filename = self.filename.replace(os.getcwd() + os.sep, "")
        self.fixit_lines = []

    def __repr__(self) -> str:
        file_ext = re.search("\.\w+", self.filename)
        return (
            "<details open>\n<summary><strong>{}:{}:{}:</strong> {}: [{}]"
            "\n\n> {}\n</summary><p>\n\n```{}\n{}```\n</p>\n</details>\n\n".format(
                self.filename,
                self.line,
                self.cols,
                self.note_type,
                self.diagnostic,
                self.note_info,
                "" if file_ext is None else file_ext.group(0)[1:],
                "".join(self.fixit_lines),
            )
        )


def parse_tidy_output() -> None:
    """Parse clang-tidy output in a file created from stdout."""
    notification = None
    with open("clang_tidy_report.txt", "r", encoding="utf-8") as tidy_out:
        for line in tidy_out.readlines():
            if re.search("^.*:\d+:\d+:\s\w+:.*\[.*\]$", line) is not None:
                notification = TidyNotification(line)
                GlobalParser.tidy_notes.append(notification)
            elif notification is not None:
                notification.fixit_lines.append(line)


def print_fixits():
    """Print out all clang-tidy notifications from stdout (which are saved to
    clang_tidy_report.txt and allocated to
    [`tidy_notes`][python_action.__init__.GlobalParser.tidy_notes]."""
    for notification in GlobalParser.tidy_notes:
        print("found", len(GlobalParser.tidy_notes), "tidy_notes")
        print(repr(notification))


if __name__ == "__main__":
    parse_tidy_output()
    print_fixits()
