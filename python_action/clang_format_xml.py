import xml.etree.ElementTree as ET

class XMLFixin:
    """A single object to represent each suggestion."""
    def __init__(self, root_tree, f_name) -> None:
        self.filename = f_name
        self.line = 0
        self.cols = 0
        self.null_len = 0
        self.text = b""


class GlobalParser:
    """Globaal variables specific to XML parser for 1 file."""
    fixits = []


def parse_format_replacements_xml(src_filename):
    """Parse XML output of replacements from clang-format."""
    src_file = open(src_filename, "r", encoding="utf-8")
    line_pos = 1
    last_new_line_pos = 0
    tree = ET.parse("clang_format_output.xml")
    fixin = XMLFixin(src_filename)
    for child in tree.getroot():
        if child.tag == "replacement":
            offset = int(child.attrib["offset"])
            while src_file.tell() != offset:
                char = src_file.read(1)
                if char == "\n":
                    line_pos += 1
                    last_new_line_pos = src_file.tell() - 1  # LF is part of offset
            fixin.cols = src_file.tell() - last_new_line_pos
            fixin.line = line_pos
            fixin.null_len = int(child.attrib["length"])
            fixin.text = "" if child.text is None else child.text
            print(
                f"offset {offset} = line {fixin.line} column {fixin.cols},"
                f" replace next {fixin.null_len} chars with:",
                repr(fixin.text)
            )
    src_file.close()
    GlobalParser.fixits.append(fixin)

if __name__ == "__main__":
    import sys
    parse_format_replacements_xml(*[sys.argv] if len(sys.argv) else "demo/demo/cpp")
