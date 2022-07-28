"""Various tests realated to the ``lines_changed_only`` option."""
import os
import logging
from pathlib import Path
import json
import re
from pytest import LogCaptureFixture
import cpp_linter
from cpp_linter.clang_format_xml import parse_format_replacements_xml
from cpp_linter.run import (
    filter_out_non_source_files,
    verify_files_are_present,
    run_clang_format,
    make_annotations,
    log_commander,
)


def test_lines_changed_only():
    """Test for lines changes in diff.

    This checks for
    1. ranges of diff chunks.
    2. ranges of lines in diff that only contain additions.
    """
    os.chdir(os.path.split(__file__)[0])
    cpp_linter.Globals.FILES = json.loads(
        Path("files.json").read_text(encoding="utf-8")
    )
    if filter_out_non_source_files(
        ext_list=["h", "cpp", "c"],
        ignored=[".github"],
        not_ignored=[],
        lines_changed_only=True,
    ):
        test_result = Path("expected_result.json").read_text(encoding="utf-8")
        for file, result in zip(
            cpp_linter.Globals.FILES["files"],
            json.loads(test_result)["files"],
        ):
            expected = result["line_filter"]["diff_chunks"]
            assert file["line_filter"]["diff_chunks"] == expected
            expected = result["line_filter"]["lines_added"]
            assert file["line_filter"]["lines_added"] == expected
    else:
        raise RuntimeError("test failed to find files")


def test_run_clang_format_diff_only(caplog: LogCaptureFixture):
    """Using the output (expected_result.json) from ``test_lines_changed_only()``,
    run clang-format with lines-changed-only set to 'true'.

    This will make sure clang-format warnings are filtered to
    only lines in the diff's chunks."""
    # log_commander.setLevel(logging.INFO)
    caplog.set_level(logging.INFO, logger=log_commander.name)
    lines_changed_only = 1  # 1 means entire diff chunks
    style = "file"  # this test includes a custom style guide
    os.chdir(os.path.split(__file__)[0])
    cpp_linter.Globals.FILES = json.loads(
        Path("expected_result.json").read_text(encoding="utf-8")
    )
    verify_files_are_present()
    for file in cpp_linter.Globals.FILES["files"]:
        filename: str = file["filename"]
        run_clang_format(
            filename=filename,
            file_obj=file,
            version="",
            style=style,
            lines_changed_only=lines_changed_only,
        )
        if os.path.getsize("clang_format_output.xml"):
            parse_format_replacements_xml(filename.replace("/", os.sep))
    make_annotations(
        style=style, file_annotations=True, lines_changed_only=lines_changed_only
    )
    record_lines = re.compile(r"\(lines (.*)\)")
    record_file = re.compile(r"File (.*)\s")
    for record in caplog.records:
        if record_lines.search(record.message) is not None:
            lines = [
                int(l.strip())
                for l in record_lines.sub("\\1", record.message).split(",")
            ]
            filename = record_file.sub("\\1", record.message)
            for file in cpp_linter.Globals.FILES["files"]:
                if file["filename"] == filename:
                    ranges = file["line_filter"]["diff_chunks"]
                    for line in lines:
                        assert line in [range(r[0], r[1]) for r in ranges]
                    break


def test_run_clang_format_diff_adds(caplog: LogCaptureFixture):
    """Using the output (expected_result.json) from ``test_lines_changed_only()``,
    run clang-format with lines-changed-only set to 'true'.

    This will make sure clang-format warnings are filtered to
    only lines in the diff containing additions."""
    # log_commander.setLevel(logging.INFO)
    caplog.set_level(logging.INFO, logger=log_commander.name)
    lines_changed_only = 2  # 2 means only lines in diff containing additions
    style = "file"  # this test includes a custom style guide
    os.chdir(os.path.split(__file__)[0])
    cpp_linter.Globals.FILES = json.loads(
        Path("expected_result.json").read_text(encoding="utf-8")
    )
    verify_files_are_present()
    for file in cpp_linter.Globals.FILES["files"]:
        filename: str = file["filename"]
        run_clang_format(
            filename=filename,
            file_obj=file,
            version="",
            style=style,
            lines_changed_only=lines_changed_only,
        )
        if os.path.getsize("clang_format_output.xml"):
            parse_format_replacements_xml(filename.replace("/", os.sep))
    make_annotations(
        style=style, file_annotations=True, lines_changed_only=lines_changed_only
    )
    record_lines = re.compile(r"\(lines (.*)\)")
    record_file = re.compile(r"File (.*)\s")
    for record in caplog.records:
        if record_lines.search(record.message) is not None:
            lines = [
                int(l.strip())
                for l in record_lines.sub("\\1", record.message).split(",")
            ]
            filename = record_file.sub("\\1", record.message)
            for file in cpp_linter.Globals.FILES["files"]:
                if file["filename"] == filename:
                    ranges = file["line_filter"]["lines_added"]
                    for line in lines:
                        assert line in [range(r[0], r[1]) for r in ranges]
                    break
