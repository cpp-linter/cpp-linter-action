"""Tests for docs/gen_io_doc.py, which generates the inputs-outputs page from action.yml."""

from __future__ import annotations

import runpy
import shutil
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
import yaml
from mkdocs.config.defaults import MkDocsConfig
from mkdocs.structure.files import Files
from mkdocs_gen_files.editor import FilesEditor

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "docs" / "gen_io_doc.py"
PAGE = "inputs-outputs.md"

RunScript = Callable[[Path], tuple[str, dict[str, Any]]]
MakeScript = Callable[[dict[str, Any], dict[str, Any]], Path]


@pytest.fixture
def run_script(tmp_path: Path) -> RunScript:
    """Run a copy of the script the way the mkdocs-gen-files plugin does.

    Returns the generated page and the edit paths the script registered.
    """

    def run(script: Path) -> tuple[str, dict[str, Any]]:
        docs_dir = tmp_path / "docs_dir"
        docs_dir.mkdir()
        config = MkDocsConfig()
        config.load_dict(
            {
                "site_name": "test",
                "docs_dir": str(docs_dir),
                "site_dir": str(tmp_path / "site"),
            }
        )
        errors, _ = config.validate()
        assert not errors
        with FilesEditor(Files([]), config, str(docs_dir)) as editor:
            runpy.run_path(str(script))
        return (docs_dir / PAGE).read_text(encoding="utf-8"), dict(editor.edit_paths)

    return run


@pytest.fixture
def make_script(tmp_path: Path) -> MakeScript:
    """Lay out an action.yml and a docs/action.yml next to the script.

    The script reads both files relative to its own path, so it is linked into
    the temporary project (coverage follows the link back to the real file).
    """

    def make(action: dict[str, Any], docs: dict[str, Any]) -> Path:
        project = tmp_path / "project"
        (project / "docs").mkdir(parents=True)
        for path, data in (
            (project / "action.yml", action),
            (project / "docs" / "action.yml", docs),
        ):
            path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
        script = project / "docs" / SCRIPT.name
        try:
            script.symlink_to(SCRIPT)
        except OSError:  # pragma: no cover - e.g. Windows without symlink privileges
            shutil.copyfile(SCRIPT, script)
        return script

    return make


def test_every_action_input_and_output_is_documented(
    run_script: RunScript, capsys: pytest.CaptureFixture[str]
):
    page, edit_paths = run_script(SCRIPT)

    out = capsys.readouterr().out
    assert "::error" not in out
    assert "::warning" not in out
    assert edit_paths == {PAGE: "gen_io_doc.py"}
    action = yaml.safe_load((REPO_ROOT / "action.yml").read_bytes())
    docs = yaml.safe_load((REPO_ROOT / "docs" / "action.yml").read_bytes())
    for name, metadata in action["inputs"].items():
        section = page.split(f"### `{name}`\n", 1)[1].split("\n### ", 1)[0]
        assert (
            f"<!-- md:version {docs['inputs'][name]['minimum-version']} -->\n"
            in section
        )
        default = metadata["default"]
        default = str(default).lower() if isinstance(default, bool) else repr(default)
        assert f"<!-- md:default {default} -->\n" in section
        assert metadata["description"].strip() in section
    for name, metadata in action["outputs"].items():
        section = page.split(f"\n### `{name}`\n", 1)[1].split("\n### ", 1)[0]
        assert (
            f"<!-- md:version {docs['outputs'][name]['minimum-version']} -->\n"
            in section
        )
        assert metadata["description"].strip() in section


ACTION: dict[str, Any] = {
    "inputs": {
        "style": {"description": "The style rules to use.\n", "default": "llvm"},
        "auto-fix": {"description": "Commit the fixes.", "default": False},
        "jobs": {"description": "The number of jobs.", "default": 0},
    },
    "outputs": {"checks-failed": {"description": "The number of failed checks."}},
}
DOCS: dict[str, Any] = {
    "inputs": {
        "style": {"minimum-version": "1.2.0", "experimental": False},
        "auto-fix": {
            "minimum-version": "2.23.0",
            "experimental": True,
            "required-permission": "contents: write #auto-fix",
        },
        "jobs": {"minimum-version": "2.11.0"},
    },
    "outputs": {"checks-failed": {"minimum-version": "1.2.0"}},
}


def test_renders_the_metadata_of_each_input_and_output(
    make_script: MakeScript, run_script: RunScript
):
    page, _ = run_script(make_script(ACTION, DOCS))

    assert page.startswith("---\ntitle: Inputs and Outputs\n---\n")
    assert (
        "## Inputs\n"
        "### `style`\n\n"
        "<!-- md:version 1.2.0 -->\n"
        "<!-- md:default 'llvm' -->\n"
        "\nThe style rules to use.\n\n"
        "### `auto-fix`\n\n"
        "<!-- md:version 2.23.0 -->\n"
        "<!-- md:default false -->\n"
        "<!-- md:flag experimental -->\n"
        "<!-- md:permission contents: write #auto-fix -->\n"
        "\nCommit the fixes.\n"
        "### `jobs`\n\n"
        "<!-- md:version 2.11.0 -->\n"
        "<!-- md:default 0 -->\n"
        "\nThe number of jobs.\n"
        "\n## Outputs\n"
    ) in page
    assert page.endswith(
        "\n### `checks-failed`\n\n"
        "<!-- md:version 1.2.0 -->\n"
        "\nThe number of failed checks.\n\n"
    )


def test_undocumented_input_is_reported_and_left_out(
    make_script: MakeScript, run_script: RunScript, capsys: pytest.CaptureFixture[str]
):
    action = {
        "inputs": {
            **ACTION["inputs"],
            "new-input": {"description": "New.", "default": ""},
        },
        "outputs": ACTION["outputs"],
    }

    page, _ = run_script(make_script(action, DOCS))

    out = capsys.readouterr().out
    assert (
        "::error file=docs/action.yml,title=Undocumented inputs field `new-input`"
        in out
    )
    assert "::Field 'new-input' not found in docs/action.yml mapping: inputs\n" in out
    assert "new-input" not in page


def test_missing_minimum_version_omits_the_version_badge(
    make_script: MakeScript, run_script: RunScript
):
    docs = {
        "inputs": {**DOCS["inputs"], "jobs": {}},
        "outputs": {"checks-failed": {}},
    }

    page, _ = run_script(make_script(ACTION, docs))

    assert "<!-- md:version 2.11.0 -->" not in page
    assert "### `jobs`\n\n<!-- md:default 0 -->\n" in page
    assert "### `checks-failed`\n\n\nThe number of failed checks.\n" in page


@pytest.mark.parametrize(
    ("action", "docs", "message"),
    [
        pytest.param(
            {"inputs": {"style": {"description": "Style."}}, "outputs": {}},
            {"inputs": {"style": {}}, "outputs": {}},
            "default value for `style` not set in action.yml",
            id="input-without-default",
        ),
        pytest.param(
            {"inputs": {"style": {"default": "llvm"}}, "outputs": {}},
            {"inputs": {"style": {}}, "outputs": {}},
            "`style` description not found in action.yml",
            id="input-without-description",
        ),
        pytest.param(
            {"inputs": {}, "outputs": {"checks-failed": {"value": "0"}}},
            {"inputs": {}, "outputs": {"checks-failed": {}}},
            "`checks-failed` description not found in action.yml",
            id="output-without-description",
        ),
        pytest.param(
            {"inputs": {}},
            {"inputs": {}, "outputs": {}},
            None,
            id="outputs-missing-from-action-yml",
        ),
        pytest.param(
            {"inputs": {}, "outputs": {}},
            {"outputs": {}},
            None,
            id="inputs-missing-from-docs",
        ),
        pytest.param(
            {"inputs": {}, "outputs": {}},
            {"inputs": {}},
            None,
            id="outputs-missing-from-docs",
        ),
    ],
)
def test_incomplete_metadata_fails_the_build(
    make_script: MakeScript,
    run_script: RunScript,
    action: dict[str, Any],
    docs: dict[str, Any],
    message: str | None,
):
    script = make_script(action, docs)

    with pytest.raises(AssertionError) as error:
        run_script(script)

    if message is not None:
        assert str(error.value) == message
