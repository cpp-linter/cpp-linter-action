"""Tests that complete coverage that aren't prone to failure."""
import logging
from pathlib import Path
from typing import List, cast, Dict, Any
import pytest
import requests
import cpp_linter
import cpp_linter.run
from cpp_linter import Globals, log_response_msg, get_line_cnt_from_cols
from cpp_linter.run import (
    log_commander,
    start_log_group,
    end_log_group,
    set_exit_code,
    list_source_files,
    get_list_of_changed_files,
)


def test_exit_override():
    """Test exit code that indicates if action encountered lining errors."""
    assert 1 == set_exit_code(1)


def test_exit_implicit():
    """Test the exit code issued when a thread comment is to be made."""
    Globals.OUTPUT = "TEST"  # fake content for a thread comment
    assert 1 == set_exit_code()


# see https://github.com/pytest-dev/pytest/issues/5997
def test_end_group(caplog: pytest.LogCaptureFixture):
    """Test the output that concludes a group of runner logs."""
    caplog.set_level(logging.INFO, logger=log_commander.name)
    log_commander.propagate = True
    end_log_group()
    messages = caplog.messages
    assert "::endgroup::" in messages


# see https://github.com/pytest-dev/pytest/issues/5997
def test_start_group(caplog: pytest.LogCaptureFixture):
    """Test the output that begins a group of runner logs."""
    caplog.set_level(logging.INFO, logger=log_commander.name)
    log_commander.propagate = True
    start_log_group("TEST")
    messages = caplog.messages
    assert "::group::TEST" in messages


@pytest.mark.parametrize(
    "url",
    [
        ("https://api.github.com/users/cpp-linter/starred"),
        pytest.param(("https://github.com/cpp-linter/repo"), marks=pytest.mark.xfail),
    ],
)
def test_response_logs(url: str):
    """Test the log output for a requests.response buffer."""
    Globals.response_buffer = requests.get(url)
    assert log_response_msg()


@pytest.mark.parametrize(
    "extensions",
    [
        (["cpp", "hpp"]),
        pytest.param(["cxx", "h"], marks=pytest.mark.xfail),
    ],
)
def test_list_src_files(extensions: List[str]):
    """List the source files in the demo folder of this repo."""
    Globals.FILES = []
    assert list_source_files(ext_list=extensions, ignored_paths=[], not_ignored=[])


def test_get_changed_files():
    """test getting a list of changed files for an event.

    This is expected to fail if a github token not supplied as an env var.
    We don't need to supply one for this test because the tested code will
    execute anyway.
    """
    cpp_linter.run.GITHUB_REPOSITORY = "cpp-linter/test-cpp-linter-action"
    cpp_linter.GITHUB_SHA = "76adde5367196cd57da5bef49a4f09af6175fd3f"
    get_list_of_changed_files()
    # pylint: disable=no-member
    assert "files" not in cast(Dict[str, Any], Globals.FILES).keys()
    # pylint: enable=no-member


@pytest.mark.parametrize("line,cols,offset", [(13, 5, 144), (19, 1, 189)])
def test_file_offset_translation(line: int, cols: int, offset: int):
    """Validate output from ``get_line_cnt_from_cols()``"""
    test_file = str(Path("demo/demo.cpp").resolve())
    assert (line, cols) == get_line_cnt_from_cols(test_file, offset)
