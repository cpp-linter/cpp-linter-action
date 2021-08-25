import xml.etree.ElementTree as ET

def parse_format_replacements_xml(src_filename):
    """Parse XML output of replacements from clang-format."""
    src_file = open(src_filename, "r", encoding="utf-8")
    line_pos = 1
    last_new_line_pos = 0
    tree = ET.parse("clang_format_output.xml")
    root = tree.getroot()
    for child in root:
        if child.tag == "replacement":
            offset = int(child.attrib["offset"])
            while src_file.tell() != offset:
                char = src_file.read(1)
                if char == "\n":
                    line_pos += 1
                    last_new_line_pos = src_file.tell() - 1  # LF is part of offset
            cols = src_file.tell() - last_new_line_pos
            print(
                f"offset {offset} = line {line_pos} column {cols},"
                f" replace next {child.attrib['length']} chars with:",
                child.text.encode("utf-8") if child.text is not None else ""
            )
            child.attrib["offset"] = line_pos
    src_file.close()

if __name__ == "__main__":
    parse_format_replacements_xml("demo/demo.c")
