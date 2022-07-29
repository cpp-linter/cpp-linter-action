"""Tests specific to specifying the compilation database path."""
import os
from typing import List
from pathlib import Path
import logging
import re
import pytest
from cpp_linter import logger
import cpp_linter.run
from cpp_linter.run import run_clang_tidy

CLANG_TIDY_COMMAND = re.compile(r"\"clang-tidy(.*)(?:\")")

ABS_DB_PATH = str(Path(Path(__file__).parent / "../../demo").resolve())


@pytest.mark.parametrize(
    "database,expected_args",
    [
        # implicit path to the compilation database
        ("", []),
        # explicit relative path to the compilation database
        ("../../demo", ["-p", ABS_DB_PATH]),
        # explicit absolute path to the compilation database
        (ABS_DB_PATH, ["-p", ABS_DB_PATH]),
    ],
)
def test_db_detection(
    caplog: pytest.LogCaptureFixture,
    database: str,
    expected_args: List[str],
):
    """test clang-tidy using a implicit path to the compilation database."""
    os.chdir(str(Path(__file__).parent))
    demo_src = "../../demo/demo.cpp"
    rel_root = str(Path(*Path(__file__).parts[-2:]))
    cpp_linter.run.RUNNER_WORKSPACE = str(
        Path(Path(__file__).parent / "../../").resolve()
    )
    caplog.set_level(logging.DEBUG, logger=logger.name)
    run_clang_tidy(
        filename=(demo_src).replace("/", os.sep),
        file_obj={},  # only used when filtering lines
        version="",
        checks="",  # let clang-tidy use a .clang-tidy config file
        lines_changed_only=0,  # analyze complete file
        database=database.replace("/", os.sep),
        repo_root=rel_root.replace("/", os.sep),
    )
    matched_args = []
    for record in caplog.records:
        msg_match = CLANG_TIDY_COMMAND.search(record.message)
        if msg_match is not None:
            matched_args = msg_match.group(0)[:-1].split()[2:]
        assert "Error while trying to load a compilation database" not in record.message
    expected_args.append(demo_src)
    assert matched_args == [a.replace("/", os.sep) for a in expected_args]
