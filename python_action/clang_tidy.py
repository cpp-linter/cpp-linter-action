"""Parse output from clang-tidy's stdout"""
import os
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
        (
            self.filename,
            self.line,
            self.cols,
            self.note_type,
            self.note_info,
        ) = notification_line.split(":")

        self.diagnostic = re.search("\[.*\]", self.note_info).group(0)
        self.note_info = self.note_info.replace(self.diagnostic, "").strip()
        self.diagnostic = self.diagnostic[1:-2]
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
    # for notification in GlobalParser.tidy_notes:
    #     print("found", len(GlobalParser.tidy_notes), "tidy_notes")
    #     print(repr(notification))


if __name__ == "__main__":
    parse_tidy_output()
