"""parse output from clang-tidy and clang-format"""
import os
import re


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
    parse_tidy_output()
