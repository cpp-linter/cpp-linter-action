"""Parse output from clang-tidy's YML format"""
import os
import yaml
from . import GlobalParser, get_line_cnt_from_cols


CWD_HEADER_GAURD = bytes(
    os.getcwd().upper().replace(os.sep, "_").replace("-", "_"), encoding="utf-8"
)  #: The constant used to trim absolute paths from header gaurd suggestions.


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
            [`TidyReplacement`][python_action.clang_tidy_yml.TidyReplacement] objects.

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
        self.replacements = []

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
        text (list): The replacement content's text (each `str` item is a line)
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
        self.text = []

    def __repr__(self) -> str:
        return (
            f"<TidyReplacement @ line {self.line} cols {self.cols} : "
            f"added lines {len(self.text)} discarded bytes {self.null_len}>"
        )

class YMLFixin:
    """A single object to represent each suggestion.

    Attributes:
        filename (str): The source file's name concerning the suggestion.
        diagnostics (list): The `list` of
            [`TidyDiagnostic`][python_action.clang_tidy_yml.TidyDiagnostic] objects
    """
    def __init__(self, filename: str) -> None:
        """
        Args:
            filename: The source file's name (with path) concerning the suggestion.
        """
        self.filename = filename
        self.diagnostics = []

    def __repr__(self) -> str:
        return (
            f"<YMLFixin ({len(self.diagnostics)} diagnostics) for file "
            f"{self.filename}>"
        )


def parse_tidy_suggestions_yml():
    """Read a YAML file from clang-tidy and create a list of suggestions from it.
    Output is saved to [`tidy_advice`][python_action.__init__.GlobalParser.tidy_advice].
    """
    with open("clang_tidy_output.yml", "r", encoding="utf-8") as yml_file:
        yml = yaml.load(yml_file, Loader=yaml.CLoader)
        fixit = YMLFixin(yml["MainSourceFile"])
        for diag_results in yml["Diagnostics"]:
            # print(diag_results)
            diag = TidyDiagnostic(diag_results["DiagnosticName"])
            diag.message = diag_results["DiagnosticMessage"]["Message"]
            line_cnt, cols = get_line_cnt_from_cols(
                yml["MainSourceFile"], diag_results["DiagnosticMessage"]["FileOffset"]
            )
            diag.line, diag.cols = (line_cnt, cols)
            for replacement in diag_results["DiagnosticMessage"]["Replacements"]:
                line_cnt, cols = get_line_cnt_from_cols(
                    yml["MainSourceFile"], replacement["Offset"]
                )
                fix = TidyReplacement(line_cnt, cols, replacement["Length"])
                fix.text = bytes(replacement["ReplacementText"], encoding="utf-8")
                if fix.text.startswith(b"header is missing header guard"):
                    print("filtering header guard suggestion (making relative to repo root)")
                    fix.text = fix.text.replace(CWD_HEADER_GAURD, b"")
                diag.replacements.append(fix)
            fixit.diagnostics.append(diag)
            # filter out absolute header gaurds
        GlobalParser.tidy_advice.append(fixit)


def print_fixits():
    """Print all [`YMLFixin`][python_action.clang_tidy_yml.YMLFixin] objects in
    [`tidy_advice`][python_action.__init__.GlobalParser.tidy_advice]."""
    for fix in GlobalParser.tidy_advice:
        for diag in fix.diagnostics:
            print(repr(diag))
            for replac in diag.replacements:
                print("    " + repr(replac), f"\n\treplace text:\n{replac.text}")


if __name__ == "__main__":
    parse_tidy_suggestions_yml()
    print_fixits()
