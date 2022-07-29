"""Tests that focus on the ``ignore`` option's parsing."""
import os
from cpp_linter.run import parse_ignore_option


def test_ignored():
    """test ignoring of a specified path."""
    ignored, not_ignored = parse_ignore_option("src")
    assert "src" in ignored and not not_ignored


def test_not_ignored():
    """test explicit inclusion of a path and ignore the root path."""
    ignored, not_ignored = parse_ignore_option("!src|")
    assert "src" in not_ignored and "" in ignored


def test_ignore_submodule():
    """test auto detection of submodules and ignore the paths appropriately."""
    os.chdir(os.path.split(__file__)[0])
    ignored, not_ignored = parse_ignore_option("!pybind11")
    for ignored_submodule in ["RF24", "RF24Network", "RF24Mesh"]:
        assert ignored_submodule in ignored
    assert "pybind11" in not_ignored