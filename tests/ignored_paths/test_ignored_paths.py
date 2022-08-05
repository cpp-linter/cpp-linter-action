"""Tests that focus on the ``ignore`` option's parsing."""
from pathlib import Path
from typing import List
import pytest
from cpp_linter.run import parse_ignore_option, is_file_in_list


@pytest.mark.parametrize(
    "user_in,is_ignored,is_not_ignored,expected",
    [
        ("src", "src", "src", [True, False]),
        ("!src|./", "", "src", [True, True]),
    ],
)
def test_ignore(
    user_in: str, is_ignored: str, is_not_ignored: str, expected: List[bool]
):
    """test ignoring of a specified path."""
    ignored, not_ignored = parse_ignore_option(user_in)
    assert expected == [
        is_file_in_list(ignored, is_ignored, "ignored"),
        is_file_in_list(not_ignored, is_not_ignored, "not ignored"),
    ]


def test_ignore_submodule(monkeypatch: pytest.MonkeyPatch):
    """test auto detection of submodules and ignore the paths appropriately."""
    monkeypatch.chdir(str(Path(__file__).parent))
    ignored, not_ignored = parse_ignore_option("!pybind11")
    for ignored_submodule in ["RF24", "RF24Network", "RF24Mesh"]:
        assert ignored_submodule in ignored
    assert "pybind11" in not_ignored
