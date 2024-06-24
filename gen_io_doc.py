from pathlib import Path
from typing import Union, Dict, Any
import yaml
import mkdocs_gen_files

FILENAME = "inputs-outputs.md"

with mkdocs_gen_files.open(FILENAME, "w") as io_doc:
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
                        message=(
                            f"Field '{k}' not found in docs/action.yml mapping:"
                        ),
                    ),
                    info_key
                )
                continue
            b_dict[info_key][k].update(v)

    doc = "".join(
        [
            "---\ntitle: Inputs and Outputs\n---\n\n" "<!--\n",
            "    this page was generated from action.yml ",
            "using the gen_io_doc.py script.\n",
            "    CHANGES TO inputs-outputs.md WILL BE LOST & OVERWRITTEN\n-->\n\n",
            "# Inputs and Outputs\n\n",
            "These are the action inputs and outputs offered by cpp-linter-action.\n",
        ]
    )
    assert "inputs" in b_dict
    doc += "\n## Inputs\n"
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
            doc += f"<!-- md:version {min_ver} -->\n"

        assert (
            "default" in input_metadata
        ), f"default value for `{action_input}` not set in action.yml"
        default: Union[str, bool] = input_metadata["default"]
        if isinstance(default, bool):
            default = str(default).lower()
        elif isinstance(default, str):
            default = repr(default)  # add quotes around value
        doc += f"<!-- md:default {default} -->\n"

        if "experimental" in input_metadata and input_metadata["experimental"] is True:
            doc += "<!-- md:flag experimental -->\n"

        if "required-permission" in input_metadata:
            permission = input_metadata["required-permission"]
            doc += f"<!-- md:permission {permission} -->\n"

        assert (
            "description" in input_metadata
        ), f"`{action_input}` description not found in action.yml"
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
            doc += f"<!-- md:version {min_ver} -->\n"

        assert (
            "description" in output_metadata
        ), f"`{action_output}` description not found in action.yml"
        doc += "\n" + output_metadata["description"] + "\n"

    print(doc, file=io_doc)

mkdocs_gen_files.set_edit_path(FILENAME, "gen_io_doc.py")
