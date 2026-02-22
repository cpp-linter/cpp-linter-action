from pathlib import Path
import re
from typing import Union, Dict, Any, cast
import yaml
import json
import sys


IO_DOC = "inputs-outputs.md"
DOC_START = "# Inputs and Outputs\n\n"


def write_io_doc() -> str:
    """Generates the content for the inputs-outputs.md file by
    merging info from action.yml and docs/action.yml"""

    action_yml = Path(__file__).parent.parent / "action.yml"
    action_doc = Path(__file__).parent / "action.yml"
    a_dict: Dict[str, Any] = yaml.safe_load(action_yml.read_bytes())
    b_dict: Dict[str, Dict[str, Any]] = yaml.safe_load(action_doc.read_bytes())

    # extract info we need from a_dict and merge into b_dict
    for info_key in b_dict:
        assert info_key in a_dict and isinstance(a_dict[info_key], dict)
        for k, v in a_dict[info_key].items():
            if k not in b_dict[info_key]:
                print(
                    "::error file=docs/action.yml,title={title}::{message}".format(
                        title=f"Undocumented {info_key} field `{k}` in actions.yml",
                        message=(f"Field '{k}' not found in docs/action.yml mapping:"),
                    ),
                    info_key,
                )
                continue
            b_dict[info_key][k].update(v)

    doc = "".join(
        [
            DOC_START,
            "<!--\nthis page was generated from action.yml ",
            "using the gen_io_doc.py script.\n",
            "    CHANGES TO inputs-outputs.md WILL BE LOST & OVERWRITTEN\n-->\n\n",
            "These are the action inputs and outputs offered by cpp-linter-action.\n",
        ]
    )
    assert "inputs" in b_dict
    doc += "\n## Inputs\n\n"
    for action_input, input_metadata in b_dict["inputs"].items():
        doc += f"### `{action_input}`\n\n"

        if "minimum-version" not in input_metadata:
            print(
                "\n::warning file={name}title={title}::{message}".format(
                    name="docs/action.yml",
                    title="Input's minimum-version not found",
                    message="minimum-version not set for input:",
                ),
                action_input,
            )
        else:
            min_ver = input_metadata["minimum-version"]
            doc += _badge_for_version(min_ver) + "\n"

        assert "default" in input_metadata, (
            f"default value for `{action_input}` not set in action.yml"
        )
        default: Union[str, bool] = input_metadata["default"]
        if isinstance(default, bool):
            default = str(default).lower()
        elif isinstance(default, str):
            default = repr(default)  # add quotes around value
        doc += _badge_for_default(default) + "\n"

        if "experimental" in input_metadata and input_metadata["experimental"] is True:
            doc += _badge_for_experimental() + "\n"

        if "required-permission" in input_metadata:
            permission = input_metadata["required-permission"]
            doc += _badge_for_permissions(permission) + "\n"

        assert "description" in input_metadata, (
            f"`{action_input}` description not found in action.yml"
        )
        doc += "\n" + input_metadata["description"] + "\n"

    assert "outputs" in b_dict
    doc += (
        "\n## Outputs\n\nThis action creates 3 output variables. Even if the linting "
        "checks fail for source files this action will still pass, but users' CI "
        "workflows can use this action's outputs to exit the workflow early if that is "
        "desired.\n"
    )
    for action_output, output_metadata in b_dict["outputs"].items():
        doc += f"\n### `{action_output}`\n\n"

        if "minimum-version" not in output_metadata:
            print(
                "\n::warning file={name}title={title}::{message}".format(
                    name="docs/action.yml",
                    title="Output's minimum-version not found",
                    message="minimum-version not set for output:",
                ),
                action_output,
            )
        else:
            min_ver = output_metadata["minimum-version"]
            doc += _badge_for_version(min_ver) + "\n"

        assert "description" in output_metadata, (
            f"`{action_output}` description not found in action.yml"
        )
        doc += "\n" + output_metadata["description"] + "\n"

    return doc


def _badge(icon: str, text: str = "") -> str:
    """Create badge"""
    return "".join(
        [
            '<span class="mdx-badge">',
            *([f'<span class="mdx-badge__icon">{icon}</span>'] if icon else []),
            *([f'<span class="mdx-badge__text">{text}</span>'] if text else []),
            "</span>",
        ]
    )


def _badge_for_version(text: str) -> str:
    """Create badge for version"""
    icon = '<i class="fa-solid fa-tag"></i>'
    href = "https://github.com/cpp-linter/cpp-linter-action/releases/" + (
        f"v{text}" if text[0:1].isdigit() else text
    )
    return _badge(
        icon=f'[{icon}]({href} "minimum version")',
        text=f'[{text}]({href} "minimum version")',
    )


def _badge_for_default(text: str) -> str:
    """Create badge for default value"""
    return _badge(icon="Default", text=f"`{text}`")


def _badge_for_permissions(args: str) -> str:
    """Create badge for required value flag"""
    match_permission = re.match(r"([^#]+)(.*)", args)
    if match_permission is None:
        raise ValueError(f"failed to parse permissions from {args}")
    permission, link = match_permission.groups()[:2]
    permission = permission.strip()
    link = "permissions.md" + link
    icon = '<i class="fa-solid fa-lock"></i>'
    return _badge(
        icon=f'[{icon}]({link} "required permissions")',
        text=f'[`{permission}`]({link} "required permission")',
    )


def _badge_for_experimental() -> str:
    """Create badge for experimental flag"""
    icon = '<i class="fa-solid fa-flask mdx-badge--heart"></i>'
    return _badge(icon=icon, text="experimental")


if __name__ == "__main__":
    if len(sys.argv) > 1:  # we check if we received any argument
        if sys.argv[1] == "supports":
            # then we are good to return an exit status code of 0, since the other argument will just be the renderer's name
            sys.exit(0)

    # load both the context and the book representations from stdin
    context, book = json.load(sys.stdin)
    # and now, we can just modify the content of the first chapter
    for item in book["items"]:
        if (
            "Chapter" in item
            and "source_path" in item["Chapter"]
            and isinstance(item["Chapter"]["source_path"], str)
            and item["Chapter"]["source_path"] == IO_DOC
            and "content" in item["Chapter"]
            and isinstance(item["Chapter"]["content"], str)
        ):
            if not cast(str, item["Chapter"]["content"]).startswith(DOC_START):
                item["Chapter"]["content"] = write_io_doc()
            break
    # we are done with the book's modification, we can just print it to stdout,
    # print(json.dumps(book, indent=2), file=sys.stderr)
    print(json.dumps(book))
