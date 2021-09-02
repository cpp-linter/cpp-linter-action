"""Parse output from clang-format's XML suggestions."""
from python_action.clang_tidy_yml import YMLFixin
import xml.etree.ElementTree as ET
from . import GlobalParser, get_line_cnt_from_cols


class XMLFixin:
    """A single object to represent each suggestion.

    Attributes:
        filename (str): The source file that the suggestion concerns
        line (int): The line number of where the suggestion starts
        cols (int): The columns number of where the suggestion starts on the line
        null_len (int): The number of bytes removed by suggestion
        text (bytes): The `bytearray` of the suggestion
    """
    def __init__(self, filename: str):
        """
        Args:
            filename: The source file's name for which the contents of the xml
                file exported by clang-tidy.
        """
        self.filename = filename  #: The source file that the suggestion concerns
        self.line = 0  #: The line number of where the suggestion starts
        self.cols = 0  #: The columns number of where the suggestion starts on the line
        self.null_len = 0  #: The number of bytes removed by suggestion
        self.text = b""  #: The `bytearray` of the suggestion

    def __repr__(self) -> str:
        return (
            f"<XMLFixin @ line {self.line} cols {self.cols} for {self.filename}>"
        )


def parse_format_replacements_xml(src_filename: str):
    """Parse XML output of replacements from clang-format. Output is saved to
    [`format_advice`][python_action.__init__.GlobalParser.format_advice].

    Args:
        src_filename: The source file's name for which the contents of the xml
            file exported by clang-tidy.
    """
    tree = ET.parse("clang_format_output.xml")
    fixin = XMLFixin(src_filename)
    for child in tree.getroot():
        if child.tag == "replacement":
            offset = int(child.attrib["offset"])
            fixin.line, fixin.cols = get_line_cnt_from_cols(src_filename, offset)
            fixin.null_len = int(child.attrib["length"])
            fixin.text = "" if child.text is None else child.text
    GlobalParser.format_advice.append(fixin)


def print_fixits():
    """Print all [`XMLFixin`][python_action.clang_format_xml.XMLFixin] objects in
    [`format_advice`][python_action.__init__.GlobalParser.format_advice]."""
    for fixin in GlobalParser.format_advice:
        if isinstance(fixin, XMLFixin):
            print(repr(fixin))

if __name__ == "__main__":
    import sys
    parse_format_replacements_xml(sys.argv[1])
    print_fixits()
