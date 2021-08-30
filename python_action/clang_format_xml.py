import xml.etree.ElementTree as ET
from . import GlobalParser, get_line_cnt_from_cols


class XMLFixin:
    """A single object to represent each suggestion."""
    def __init__(self, f_name) -> None:
        self.filename = f_name
        self.line = 0
        self.cols = 0
        self.null_len = 0
        self.text = b""


def parse_format_replacements_xml(src_filename):
    """Parse XML output of replacements from clang-format."""
    tree = ET.parse("clang_format_output.xml")
    fixin = XMLFixin(src_filename)
    for child in tree.getroot():
        if child.tag == "replacement":
            offset = int(child.attrib["offset"])
            fixin.line, fixin.cols = get_line_cnt_from_cols(src_filename, offset)
            fixin.null_len = int(child.attrib["length"])
            fixin.text = "" if child.text is None else child.text
            # print(
            #     f"offset {offset} = line {fixin.line} column {fixin.cols},"
            #     f" replace next {fixin.null_len} chars with:",
            #     repr(fixin.text)
            # )
    GlobalParser.advice.append(fixin)

if __name__ == "__main__":
    import sys
    parse_format_replacements_xml(sys.argv[1])
