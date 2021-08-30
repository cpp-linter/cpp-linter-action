"""parse output from clang-tidy and clang-format"""
import os
import re
from . import GlobalParser


class TidyNotification:
    """Create a object that decodes info from the clang-tidy output's initial line that
    details a specific notification."""

    def __init__(self, notification_line):
        (
            self.filename,
            self.line,
            self.cols,
            self.note_type,
            self.note_info,
        ) = notification_line.split(":")
        self.diagnostic = re.search("\[.*\]", self.note_info).group(0)
        self.note_info = self.note_info.replace(self.diagnostic, "").strip()
        self.note_type = self.note_type.strip()
        self.diagnostic = self.diagnostic[1:-2]
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

def parse_tidy_output():
    """Parse clang-tidy output in a file created from stdout"""
    notification = None
    with open("clang_tidy_report.txt", "r", encoding="utf-8") as tidy_out:
        for line in tidy_out.readlines():
            if re.search("^.*:\d+:\d+:\s\w+:.*\[.*\]$", line) is not None:
                notification = TidyNotification(line)
                GlobalParser.fixits.append(notification)
            elif notification is not None:
                notification.fixit_lines.append(line)
    # for notification in GlobalParser.fixits:
    #     print("found", len(GlobalParser.fixits), "fixits")
    #     print(repr(notification))


if __name__ == "__main__":
    parse_tidy_output()
