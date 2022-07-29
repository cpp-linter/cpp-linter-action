"""Tests specific to specifying the compilation database path."""
import os
from typing import Optional, List
from pathlib import Path
import logging
import re
import pytest
from cpp_linter import logger
import cpp_linter.run
from cpp_linter.run import run_clang_tidy

CLANG_TIDY_COMMAND = re.compile(r"\"clang-tidy(.*)(?:\")")


@pytest.mark.parametrize(
    "database,repo_root,runner,expected_args",
    [
        # implicit path to the compilation database
        ("", "../../", "", ["../../demo/demo.cpp"]),
        # explicit relative path to the compilation database
        (
            "demo",
            ".",  # only used if RUNNER_WORKSPACE is given
            "",  # RUNNER_WORKSPACE not set
            [
                "-p",
                str(Path(Path(__file__).parent / "../../demo").resolve()),
                "../../demo/demo.cpp",
            ],
        ),
        # explicit absolute path to the compilation database
        (
            str(Path(Path(__file__).parent / "../../demo").resolve()),
            ".",  # only used if RUNNER_WORKSPACE is given
            "",  # RUNNER_WORKSPACE not set
            [
                "-p",
                str(Path(Path(__file__).parent / "../../demo").resolve()),
                "../../demo/demo.cpp",
            ],
        ),
        # explicit relative path to the compilation database w/ RUNNER_WORKSPACE
        (
            "demo",
            ".",  # only used if db path is abs
            str(Path(Path(__file__).parent / "../../").resolve()),
            [
                "-p",
                str(Path(Path(__file__).parent / "../../demo").resolve()),
                "../../demo/demo.cpp",
            ],
        ),
        # explicit absolute path to the compilation database w/ RUNNER_WORKSPACE
        (
            str(Path(Path(__file__).parent / "../../demo").resolve()),
            ".",  # overridden by abs path to db
            str(Path(Path(__file__).parent / "../../").resolve()),
            [
                "-p",
                str(Path(Path(__file__).parent / "../../demo").resolve()),
                "../../demo/demo.cpp",
            ],
        ),
    ],
)
def test_db_detection(
    caplog: pytest.LogCaptureFixture,
    database: str,
    repo_root: str,
    runner: Optional[str],
    expected_args: List[str],
):
    """test clang-tidy using a implicit path to the compilation database."""
    os.chdir(str(Path(__file__).parent))
    if runner:
        cpp_linter.run.RUNNER_WORKSPACE = runner
    caplog.set_level(logging.DEBUG, logger=logger.name)
    run_clang_tidy(
        filename=("../../demo/demo.cpp").replace("/", os.sep),
        file_obj={},  # only used when filtering lines
        version="",
        checks="",  # let clang-tidy use a .clang-tidy config file
        lines_changed_only=0,  # analyze complete file
        database=database.replace("/", os.sep),
        repo_root=repo_root.replace("/", os.sep),
    )
    matched_args = []
    for record in caplog.records:
        msg_match = CLANG_TIDY_COMMAND.search(record.message)
        if msg_match is not None:
            matched_args = msg_match.group(0)[:-1].split()[2:]
        assert "Error while trying to load a compilation database" not in record.message
    assert matched_args == [a.replace("/", os.sep) for a in expected_args]
