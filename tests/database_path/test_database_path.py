"""Tests specific to specifying the compilation database path."""
import os
import logging
import re
from pytest import LogCaptureFixture
from cpp_linter import logger
import cpp_linter.run
from cpp_linter.run import run_clang_tidy

CLANG_TIDY_COMMAND = re.compile(r"\"clang-tidy(.*)(?:\")")


def test_db_implicit(caplog: LogCaptureFixture):
    """test clang-tidy using a implicit path to the compilation database."""
    os.chdir(os.path.split(__file__)[0])
    caplog.set_level(logging.DEBUG, logger=logger.name)
    run_clang_tidy(
        filename="../../demo/demo.cpp",
        file_obj={},  # only used when using a line filter
        version="",  # use whatever default is available on the test platform
        checks="",  # let clang-tidy use a .clang-tidy config file
        lines_changed_only=0,  # analyze complete file
        database="",
        repo_root="../../",  # relative to this test directory
    )
    matched_args = []
    for record in caplog.records:
        msg_match = CLANG_TIDY_COMMAND.search(record.message)
        if msg_match is not None:
            matched_args = msg_match.group(0)[:-1].split()[1:]
            matched_args = [m.replace("\\", "/") for m in matched_args]
        assert "Error while trying to load a compilation database" not in record.message
    assert matched_args == [
        "--export-fixes=clang_tidy_output.yml",
        "../../demo/demo.cpp",
    ]


def test_db_explicit_rel(caplog: LogCaptureFixture):
    """test clang-tidy using a explicit relative path to the compilation database."""
    os.chdir(os.path.split(__file__)[0])
    caplog.set_level(logging.DEBUG, logger=logger.name)
    run_clang_tidy(
        filename="../../demo/demo.cpp",
        file_obj={},  # only used when using a line filter
        version="",  # use whatever default is available on the test platform
        checks="",  # let clang-tidy use a .clang-tidy config file
        lines_changed_only=0,  # analyze complete file
        database="../../demo",
        repo_root="../../",  # relative to this test directory
    )
    matched_args = []
    for record in caplog.records:
        msg_match = CLANG_TIDY_COMMAND.search(record.message)
        if msg_match is not None:
            matched_args = msg_match.group(0)[:-1].split()[1:]
            matched_args = [m.replace("\\", "/") for m in matched_args]
        assert "Error while trying to load a compilation database" not in record.message
    assert matched_args == [
        "--export-fixes=clang_tidy_output.yml",
        "-p",
        "../../demo",
        "../../demo/demo.cpp",
    ]


def test_db_explicit_abs(caplog: LogCaptureFixture):
    """test clang-tidy using a explicit absolute path to the compilation database."""
    os.chdir(os.path.split(__file__)[0])
    caplog.set_level(logging.DEBUG, logger=logger.name)
    run_clang_tidy(
        filename="../../demo/demo.cpp",
        file_obj={},  # only used when using a line filter
        version="",  # use whatever default is available on the test platform
        checks="",  # let clang-tidy use a .clang-tidy config file
        lines_changed_only=0,  # analyze complete file
        database=os.path.abspath("../../demo"),
        repo_root="../../",  # relative to this test directory
    )
    matched_args = []
    for record in caplog.records:
        msg_match = CLANG_TIDY_COMMAND.search(record.message)
        if msg_match is not None:
            matched_args = msg_match.group(0)[:-1].split()[1:]
            matched_args = [m.replace("\\", "/") for m in matched_args]
        assert "Error while trying to load a compilation database" not in record.message
    assert matched_args == [
        "--export-fixes=clang_tidy_output.yml",
        "-p",
        os.path.abspath("../../demo").replace("\\", "/"),
        "../../demo/demo.cpp",
    ]


def test_db_explicit_rel_runner(caplog: LogCaptureFixture):
    """test clang-tidy using a explicit relative path to the compilation database
    with the added context of a RUNNER_WORKSPACE env var."""
    os.chdir(os.path.split(__file__)[0])
    cpp_linter.run.RUNNER_WORKSPACE = os.path.abspath("../../")
    caplog.set_level(logging.DEBUG, logger=logger.name)
    run_clang_tidy(
        filename="../../demo/demo.cpp",
        file_obj={},  # only used when using a line filter
        version="",  # use whatever default is available on the test platform
        checks="",  # let clang-tidy use a .clang-tidy config file
        lines_changed_only=0,  # analyze complete file
        database="demo",
        repo_root=".",  # should be overridden by the RUNNER_WORKSPACE value
    )
    matched_args = []
    for record in caplog.records:
        msg_match = CLANG_TIDY_COMMAND.search(record.message)
        if msg_match is not None:
            matched_args = msg_match.group(0)[:-1].split()[1:]
            matched_args = [m.replace("\\", "/") for m in matched_args]
        assert "Error while trying to load a compilation database" not in record.message
    assert matched_args == [
        "--export-fixes=clang_tidy_output.yml",
        "-p",
        os.path.abspath("../../demo").replace("\\", "/"),
        "../../demo/demo.cpp",
    ]


def test_db_explicit_abs_runner(caplog: LogCaptureFixture):
    """test clang-tidy using a explicit absolute path to the compilation database
    with the added context of a RUNNER_WORKSPACE env var."""
    os.chdir(os.path.split(__file__)[0])
    cpp_linter.run.RUNNER_WORKSPACE = "../../"
    caplog.set_level(logging.DEBUG, logger=logger.name)
    run_clang_tidy(
        filename="../../demo/demo.cpp",
        file_obj={},  # only used when using a line filter
        version="",  # use whatever default is available on the test platform
        checks="",  # let clang-tidy use a .clang-tidy config file
        lines_changed_only=0,  # analyze complete file
        database=os.path.abspath("../../demo"),
        repo_root=".",  # should be overridden by the RUNNER_WORKSPACE value
    )
    matched_args = []
    for record in caplog.records:
        msg_match = CLANG_TIDY_COMMAND.search(record.message)
        if msg_match is not None:
            matched_args = msg_match.group(0)[:-1].split()[1:]
            matched_args = [m.replace("\\", "/") for m in matched_args]
        assert "Error while trying to load a compilation database" not in record.message
    assert matched_args == [
        "--export-fixes=clang_tidy_output.yml",
        "-p",
        os.path.abspath("../../demo").replace("\\", "/"),
        "../../demo/demo.cpp",
    ]
