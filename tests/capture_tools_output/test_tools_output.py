"""Various tests related to the ``lines_changed_only`` option."""
import os
import logging
from typing import Dict, Any, cast, List, Optional
from pathlib import Path
import json
import re
import pytest
import cpp_linter
from cpp_linter.run import (
    filter_out_non_source_files,
    verify_files_are_present,
    capture_clang_tools_output,
    make_annotations,
    log_commander,
)
from cpp_linter.thread_comments import list_diff_comments

CLANG_VERSION = os.getenv("CLANG_VERSION", "12")


@pytest.mark.parametrize(
    "extensions", [(["c"]), pytest.param(["h"], marks=pytest.mark.xfail)]
)
def test_lines_changed_only(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    extensions: List[str],
):
    """Test for lines changes in diff.

    This checks for
    1. ranges of diff chunks.
    2. ranges of lines in diff that only contain additions.
    """
    monkeypatch.chdir(str(Path(__file__).parent))
    caplog.set_level(logging.DEBUG, logger=cpp_linter.logger.name)
    cpp_linter.Globals.FILES = json.loads(
        Path("event_files.json").read_text(encoding="utf-8")
    )
    if filter_out_non_source_files(
        ext_list=extensions,
        ignored=[".github"],
        not_ignored=[],
    ):
        test_result = Path("expected_result.json").read_text(encoding="utf-8")
        for file, result in zip(
            cpp_linter.Globals.FILES,
            json.loads(test_result),
        ):
            expected = result["line_filter"]["diff_chunks"]
            assert file["line_filter"]["diff_chunks"] == expected
            expected = result["line_filter"]["lines_added"]
            assert file["line_filter"]["lines_added"] == expected
    else:
        raise RuntimeError("test failed to find files")


TEST_REPO = re.compile(r".*github.com/(?:\w|\-|_)+/((?:\w|\-|_)+)/.*")


@pytest.fixture(autouse=True)
def setup_test_repo(monkeypatch: pytest.MonkeyPatch) -> None:
    """Setup a test repo to run the rest of the tests in this module."""
    test_root = Path(__file__).parent
    cpp_linter.Globals.FILES = json.loads(
        Path(test_root / "expected_result.json").read_text(encoding="utf-8")
    )
    # flush output from any previous tests
    cpp_linter.Globals.OUTPUT = ""
    cpp_linter.GlobalParser.format_advice = []
    cpp_linter.GlobalParser.tidy_notes = []
    cpp_linter.GlobalParser.tidy_advice = []

    repo_root = TEST_REPO.sub("\\1", cpp_linter.Globals.FILES[0]["blob_url"])
    return_path = test_root / repo_root
    if not return_path.exists():
        return_path.mkdir()
    monkeypatch.chdir(str(return_path))
    verify_files_are_present()


def match_file_json(filename: str) -> Optional[Dict[str, Any]]:
    """A helper function to match a given filename with a file's JSON object."""
    for file in cpp_linter.Globals.FILES:
        if file["filename"] == filename:
            return file
    print("file", filename, "not found in expected_result.json")
    return None


RECORD_FILE = re.compile(r".*file=(.*?),.*")
FORMAT_RECORD = re.compile(r"Run clang-format on ")
FORMAT_RECORD_LINES = re.compile(r".*\(lines (.*)\).*")
TIDY_RECORD = re.compile(r":\d+:\d+ \[.*\]::")
TIDY_RECORD_LINE = re.compile(r".*,line=(\d+).*")


@pytest.mark.parametrize(
    "lines_changed_only", [0, 1, 2], ids=["all lines", "only diff", "only added"]
)
@pytest.mark.parametrize("style", ["file", "llvm", "google"])
def test_format_annotations(
    caplog: pytest.LogCaptureFixture,
    lines_changed_only: int,
    style: str,
):
    """Test clang-format annotations."""
    capture_clang_tools_output(
        version=CLANG_VERSION,
        checks="-*",  # disable clang-tidy output
        style=style,
        lines_changed_only=lines_changed_only,
        database="",
        repo_root="",
    )
    assert "Output from `clang-tidy`" not in cpp_linter.Globals.OUTPUT
    caplog.set_level(logging.INFO, logger=log_commander.name)
    log_commander.propagate = True
    make_annotations(
        style=style, file_annotations=True, lines_changed_only=lines_changed_only
    )
    for message in [r.message for r in caplog.records if r.levelno == logging.INFO]:
        if FORMAT_RECORD.search(message) is not None:
            lines = [
                int(l.strip())
                for l in FORMAT_RECORD_LINES.sub("\\1", message).split(",")
            ]
            file = match_file_json(RECORD_FILE.sub("\\1", message).replace("\\", "/"))
            if file is None:
                continue
            ranges = cpp_linter.range_of_changed_lines(file, lines_changed_only)
            if ranges:  # an empty list if lines_changed_only == 0
                for line in lines:
                    assert line in ranges
        else:
            raise RuntimeWarning(f"unrecognized record: {message}")


@pytest.mark.parametrize(
    "lines_changed_only", [0, 1, 2], ids=["all lines", "only diff", "only added"]
)
@pytest.mark.parametrize(
    "checks",
    [
        "",
        "boost-*,bugprone-*,performance-*,readability-*,portability-*,modernize-*,"
        "clang-analyzer-*,cppcoreguidelines-*",
    ],
    ids=["config file", "action defaults"],
)
def test_tidy_annotations(
    caplog: pytest.LogCaptureFixture,
    lines_changed_only: int,
    checks: str,
):
    """Test clang-tidy annotations."""
    capture_clang_tools_output(
        version=CLANG_VERSION,
        checks=checks,
        style="",  # disable clang-format output
        lines_changed_only=lines_changed_only,
        database="",
        repo_root="",
    )
    assert "Run `clang-format` on the following files" not in cpp_linter.Globals.OUTPUT
    caplog.set_level(logging.INFO, logger=log_commander.name)
    log_commander.propagate = True
    make_annotations(
        style="", file_annotations=True, lines_changed_only=lines_changed_only
    )
    for message in [r.message for r in caplog.records if r.levelno == logging.INFO]:
        if TIDY_RECORD.search(message) is not None:
            line = int(TIDY_RECORD_LINE.sub("\\1", message))
            file = match_file_json(RECORD_FILE.sub("\\1", message).replace("\\", "/"))
            if file is None:
                continue
            ranges = cpp_linter.range_of_changed_lines(file, lines_changed_only)
            if ranges:  # an empty list if lines_changed_only == 0
                assert line in ranges
        else:
            raise RuntimeWarning(f"unrecognized record: {message}")


@pytest.mark.parametrize("lines_changed_only", [1, 2], ids=["only diff", "only added"])
def test_diff_comment(lines_changed_only: int):
    """Tests code that isn't actually used (yet) for posting
    comments (not annotations) in the event's diff.

    Remember, diff comments should only focus on lines in the diff."""
    capture_clang_tools_output(
        version=CLANG_VERSION,
        checks="",
        style="file",
        lines_changed_only=lines_changed_only,
        database="",
        repo_root="",
    )
    diff_comments = list_diff_comments(lines_changed_only)
    # output = Path(__file__).parent / "diff_comments.json"
    # output.write_text(json.dumps(diff_comments, indent=2), encoding="utf-8")
    for comment in diff_comments:
        file = match_file_json(cast(str, comment["path"]))
        if file is None:
            continue
        ranges = cpp_linter.range_of_changed_lines(file, lines_changed_only)
        assert comment["line"] in ranges
