"""Parse output from clang-tidy's YML format"""
from pathlib import Path, PurePath
from typing import List
import yaml
from . import GlobalParser, get_line_cnt_from_cols, logger


CWD_HEADER_GUARD = bytes(
    "_".join([p.upper().replace("-", "_") for p in Path.cwd().parts]), encoding="utf-8"
)  #: The constant used to trim absolute paths from header guard suggestions.


class TidyDiagnostic:
    """Create an object that represents a diagnostic output found in the
    YAML exported from clang-tidy.

    Attributes:
        name (str): The diagnostic name
        message (str): The diagnostic message
        line (int): The line number that triggered the diagnostic
        cols (int): The columns of the `line` that triggered the diagnostic
        null_len (int): The number of bytes replaced by suggestions
        replacements (list): The `list` of
            [`TidyReplacement`][cpp_linter.clang_tidy_yml.TidyReplacement] objects.

    """

    def __init__(self, diagnostic_name: str):
        """
        Args:
            diagnostic_name: The name of the check that got triggered.
        """
        self.name = diagnostic_name
        self.message = ""
        self.line = 0
        self.cols = 0
        self.null_len = 0
        self.replacements: List["TidyReplacement"] = []

    def __repr__(self):
        """a str representation of all attributes."""
        return (
            f"<TidyDiagnostic {self.name} @ line {self.line} cols {self.cols} : "
            f"{len(self.replacements)} replacements>"
        )


class TidyReplacement:
    """Create an object representing a clang-tidy suggested replacement.

    Attributes:
        line (int): The replacement content's starting line
        cols (int): The replacement content's starting columns
        null_len (int): The number of bytes discarded from `cols`
        text (bytes): The replacement content's text.
    """

    def __init__(self, line_cnt: int, cols: int, length: int):
        """
        Args:
            line_cnt: The replacement content's starting line
            cols: The replacement content's starting columns
            length: The number of bytes discarded from `cols`
        """
        self.line = line_cnt
        self.cols = cols
        self.null_len = length
        self.text: bytes = b""

    def __repr__(self) -> str:
        return (
            f"<TidyReplacement @ line {self.line} cols {self.cols} : "
            f"added lines {len(self.text)} discarded bytes {self.null_len}>"
        )


class YMLFixit:
    """A single object to represent each suggestion.

    Attributes:
        filename (str): The source file's name concerning the suggestion.
        diagnostics (list): The `list` of
            [`TidyDiagnostic`][cpp_linter.clang_tidy_yml.TidyDiagnostic] objects.
    """

    def __init__(self, filename: str) -> None:
        """
        Args:
            filename: The source file's name (with path) concerning the suggestion.
        """
        self.filename = PurePath(filename).relative_to(Path.cwd()).as_posix()
        self.diagnostics: List[TidyDiagnostic] = []

    def __repr__(self) -> str:
        return (
            f"<YMLFixit ({len(self.diagnostics)} diagnostics) for file "
            f"{self.filename}>"
        )


def parse_tidy_suggestions_yml():
    """Read a YAML file from clang-tidy and create a list of suggestions from it.
    Output is saved to [`tidy_advice`][cpp_linter.GlobalParser.tidy_advice].
    """
    yml_file = Path("clang_tidy_output.yml").read_text(encoding="utf-8")
    yml = yaml.safe_load(yml_file)
    fixit = YMLFixit(yml["MainSourceFile"])
    for diag_results in yml["Diagnostics"]:
        diag = TidyDiagnostic(diag_results["DiagnosticName"])
        diag.message = diag_results["DiagnosticMessage"]["Message"]
        diag.line, diag.cols = get_line_cnt_from_cols(
            yml["MainSourceFile"], diag_results["DiagnosticMessage"]["FileOffset"]
        )
        for replacement in diag_results["DiagnosticMessage"]["Replacements"]:
            line_cnt, cols = get_line_cnt_from_cols(
                yml["MainSourceFile"], replacement["Offset"]
            )
            fix = TidyReplacement(line_cnt, cols, replacement["Length"])
            fix.text = bytes(replacement["ReplacementText"], encoding="utf-8")
            if fix.text.startswith(b"header is missing header guard"):
                logger.debug(
                    "filtering header guard suggestion (making relative to repo root)"
                )
                fix.text = fix.text.replace(CWD_HEADER_GUARD, b"")
            diag.replacements.append(fix)
        fixit.diagnostics.append(diag)
        # filter out absolute header guards
    GlobalParser.tidy_advice.append(fixit)
