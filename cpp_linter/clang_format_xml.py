"""Parse output from clang-format's XML suggestions."""
import os
import xml.etree.ElementTree as ET
from . import GlobalParser, get_line_cnt_from_cols


class FormatReplacement:
    """An object representing a single replacement.

    Attributes:
        cols (int): The columns number of where the suggestion starts on the line
        null_len (int): The number of bytes removed by suggestion
        text (str): The `bytearray` of the suggestion
    """

    def __init__(self, cols: int, null_len: int, text: str) -> None:
        """
        Args:
            cols: The columns number of where the suggestion starts on the line
            null_len: The number of bytes removed by suggestion
            text: The `bytearray` of the suggestion
        """
        self.cols = cols
        self.null_len = null_len
        self.text = text

    def __repr__(self) -> str:
        return (
            f"<FormatReplacement at cols {self.cols} removes {self.null_len} bytes"
            f" adds {len(self.text)} bytes>"
        )


class FormatReplacementLine:
    """An object that represents a replacement(s) for a single line.

    Attributes:
        line (int): The line number of where the suggestion starts
        replacements (list): A list of
            [`FormatReplacement`][cpp_linter.clang_format_xml.FormatReplacement]
            object(s) representing suggestions.
    """

    def __init__(self, line_numb: int):
        """
        Args:
            line_numb: The line number of about the replacements
        """
        self.line = line_numb
        self.replacements = []

    def __repr__(self):
        return (
            f"<FormatReplacementLine @ line {self.line} "
            f"with {len(self.replacements)} replacements>"
        )


class XMLFixit:
    """A single object to represent each suggestion.

    Attributes:
        filename (str): The source file that the suggestion concerns.
        replaced_lines (list): A list of
            [`FormatReplacementLine`][
                cpp_linter.clang_format_xml.FormatReplacementLine]
            representing replacement(s) on a single line.
    """

    def __init__(self, filename: str):
        """
        Args:
            filename: The source file's name for which the contents of the xml
                file exported by clang-tidy.
        """
        self.filename = filename.replace(os.sep, "/")
        self.replaced_lines = []

    def __repr__(self) -> str:
        return (
            f"<XMLFixit with {len(self.replaced_lines)} lines of "
            f"replacements for {self.filename}>"
        )

    def log_command(self, style: str) -> str:
        """Output a notification as a github log command.

        !!! info See Also
            - [An error message](https://docs.github.com/en/actions/learn-github-
              actions/workflow-commands-for-github-actions#setting-an-error-message)
            - [A warning message](https://docs.github.com/en/actions/learn-github-
              actions/workflow-commands-for-github-actions#setting-a-warning-message)
            - [A notice message](https://docs.github.com/en/actions/learn-github-
              actions/workflow-commands-for-github-actions#setting-a-notice-message)

        Args:
            style: The chosen code style guidelines.
        """
        if style not in ("llvm", "google", "webkit", "mozilla", "gnu"):
            # potentially the style parameter could be a str of JSON/YML syntax
            style = "Custom"
        else:
            if style.startswith("llvm") or style.startswith("gnu"):
                style = style.upper()
            else:
                style = style.title()

        return (
            "::notice file={name},title=Run clang-format on {name}::"
            "File {name} (lines {lines}): Code does not conform to {style_guide} "
            "style guidelines.".format(
                name=self.filename,
                lines=", ".join(str(f.line) for f in self.replaced_lines),
                style_guide=style,
            )
        )


def parse_format_replacements_xml(src_filename: str):
    """Parse XML output of replacements from clang-format. Output is saved to
    [`format_advice`][cpp_linter.GlobalParser.format_advice].

    Args:
        src_filename: The source file's name for which the contents of the xml
            file exported by clang-tidy.
    """
    tree = ET.parse("clang_format_output.xml")
    fixit = XMLFixit(src_filename)
    for child in tree.getroot():
        if child.tag == "replacement":
            offset = int(child.attrib["offset"])
            line, cols = get_line_cnt_from_cols(src_filename, offset)
            null_len = int(child.attrib["length"])
            text = "" if child.text is None else child.text
            fix = FormatReplacement(cols, null_len, text)
            if not fixit.replaced_lines or (
                fixit.replaced_lines and line != fixit.replaced_lines[-1].line
            ):
                line_fix = FormatReplacementLine(line)
                line_fix.replacements.append(fix)
                fixit.replaced_lines.append(line_fix)
            elif fixit.replaced_lines and line == fixit.replaced_lines[-1].line:
                fixit.replaced_lines[-1].replacements.append(fix)
    GlobalParser.format_advice.append(fixit)


def print_fixits():
    """Print all [`XMLFixit`][cpp_linter.clang_format_xml.XMLFixit] objects in
    [`format_advice`][cpp_linter.GlobalParser.format_advice]."""
    for fixit in GlobalParser.format_advice:
        print(repr(fixit))
        for line_fix in fixit.replaced_lines:
            print("    " + repr(line_fix))
            for fix in line_fix.replacements:
                print("\t" + repr(fix))


if __name__ == "__main__":
    import sys

    parse_format_replacements_xml(sys.argv[1])
    print_fixits()
