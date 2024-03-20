from pathlib import Path
from typing import Union
import yaml
import mkdocs_gen_files

FILENAME = "inputs-outputs.md"

with mkdocs_gen_files.open(FILENAME, "w") as io_doc:
    action_yml = Path(__file__).parent.parent / "action.yml"
    action_dict = yaml.safe_load(action_yml.read_bytes())
    doc = "".join(
        [
            "---\ntitle: Inputs and Outputs\n---\n\n"
            "<!--\n",
            "    this page was generated from action.yml ",
            "using the gen_io_doc.py script.\n",
            "    CHANGES TO inputs-outputs.md WILL BE LOST & OVERWRITTEN\n-->\n\n",
            "# Inputs and Outputs\n\n",
            "These are the action inputs and outputs offered by cpp-linter-action.\n",
        ]
    )
    assert "inputs" in action_dict
    doc += "\n## Inputs\n"
    for action_input, input_metadata in action_dict["inputs"].items():
        doc += f"### `{action_input}`\n\n"

        assert "minimum-version" in input_metadata
        min_ver = input_metadata["minimum-version"]
        doc += f"<!-- md:version {min_ver} -->\n"

        assert "default" in input_metadata
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

        assert "description" in input_metadata
        doc += "\n" + input_metadata["description"] + "\n"

    assert "outputs" in action_dict
    doc += (
        "\n## Outputs\n\nThis action creates 3 output variables. Even if the linting "
        "checks fail for source files this action will still pass, but users' CI "
        "workflows can use this action's outputs to exit the workflow early if that is "
        "desired.\n"
    )
    for action_output, output_metadata in action_dict["outputs"].items():
        doc += f"\n### `{action_output}`\n\n"

        assert "minimum-version" in output_metadata
        min_ver = output_metadata["minimum-version"]
        doc += f"<!-- md:version {min_ver} -->\n"


        assert "description" in output_metadata
        doc += "\n" + output_metadata["description"] + "\n"

    print(doc, file=io_doc)

mkdocs_gen_files.set_edit_path(FILENAME, "gen_io_doc.py")
