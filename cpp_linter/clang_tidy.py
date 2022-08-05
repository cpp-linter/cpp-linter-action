"""Parse output from clang-tidy's stdout"""
import os
import re
from typing import Tuple, Union, List, cast
from . import GlobalParser

NOTE_HEADER = re.compile(r"^(.*):(\d+):(\d+):\s(\w+):(.*)\[(.*)\]$")


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
        fixit_lines (list): A `list` of lines (`str`) for the code-block in the
            notification.
    """

    def __init__(
        self,
        notification_line: Tuple[str, Union[int, str], Union[int, str], str, str, str],
    ):
        """
        Args:
            notification_line: The first line in the notification parsed into a tuple of
                string that represent the different components of the notification's
                details.
        """
        # logger.debug("Creating tidy note from line %s", notification_line)
        (
            self.filename,
            self.line,
            self.cols,
            self.note_type,
            self.note_info,
            self.diagnostic,
        ) = notification_line

        self.note_info = self.note_info.strip()
        self.note_type = self.note_type.strip()
        self.line = int(self.line)
        self.cols = int(self.cols)
        self.filename = self.filename.replace(os.getcwd() + os.sep, "")
        self.fixit_lines: List[str] = []

    def __repr__(self) -> str:
        concerned_code = ""
        if self.fixit_lines:
            concerned_code = "```{}\n{}```\n".format(
                os.path.splitext(self.filename)[1],
                "".join(self.fixit_lines),
            )
        return (
            "<details open>\n<summary><strong>{}:{}:{}:</strong> {}: [{}]"
            "\n\n> {}\n</summary><p>\n\n{}</p>\n</details>\n\n".format(
                self.filename,
                self.line,
                self.cols,
                self.note_type,
                self.diagnostic,
                self.note_info,
                concerned_code,
            )
        )

    def log_command(self) -> str:
        """Output the notification as a github log command.

        !!! info See Also
            - [An error message](https://docs.github.com/en/actions/learn-github-
              actions/workflow-commands-for-github-actions#setting-an-error-message)
            - [A warning message](https://docs.github.com/en/actions/learn-github-
              actions/workflow-commands-for-github-actions#setting-a-warning-message)
            - [A notice message](https://docs.github.com/en/actions/learn-github-
              actions/workflow-commands-for-github-actions#setting-a-notice-message)
        """
        filename = self.filename.replace("\\", "/")
        return (
            "::{} file={file},line={line},title={file}:{line}:{cols} [{diag}]::"
            "{info}".format(
                "notice" if self.note_type.startswith("note") else self.note_type,
                file=filename,
                line=self.line,
                cols=self.cols,
                diag=self.diagnostic,
                info=self.note_info,
            )
        )


def parse_tidy_output() -> None:
    """Parse clang-tidy output in a file created from stdout."""
    notification = None
    with open("clang_tidy_report.txt", "r", encoding="utf-8") as tidy_out:
        for line in tidy_out.readlines():
            match = re.match(NOTE_HEADER, line)
            if match is not None:
                notification = TidyNotification(
                    cast(
                        Tuple[str, Union[int, str], Union[int, str], str, str, str],
                        match.groups(),
                    )
                )
                GlobalParser.tidy_notes.append(notification)
            elif notification is not None:
                # append lines of code that are part of
                # the previous line's notification
                notification.fixit_lines.append(line)
