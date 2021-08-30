"""parse output from clang-tidy and clang-format"""
import os
import yaml
from . import GlobalParser, get_line_cnt_from_cols

CWD_HEADER_GAURD = bytes(
    os.getcwd().upper().replace("/", "_").replace("-", "_"), encoding="utf-8"
)


class TidyDiagnostic:
    """Create an object that represents a diagnostic output found in the
    YAML exported from clang-tidy"""

    def __init__(self, diagnostic_name):
        self.name, self.message = (diagnostic_name, "")
        self.line, self.cols, self.null_len, self.replacements = (0, 0, 0, [])


class TidyReplacement:
    """Create an object representing a clang-tidy suggested replacement"""

    def __init__(self, line_cnt, cols, length):
        self.line = line_cnt
        self.cols = cols
        self.null_len = length
        self.text = []


class YMLFixin:
    """A single object to represent each suggestion."""
    def __init__(self, f_name) -> None:
        self.filename = f_name
        self.diagnostics = []


def parse_tidy_suggestions_yml():
    """Read a YAML file from clang-tidy and create a list of suggestions from it."""
    with open("clang_tidy_output.yml", "r", encoding="utf-8") as yml_file:
        yml = yaml.load(yml_file, Loader=yaml.CLoader)
        fixit = YMLFixin(yml["MainSourceFile"])
        for diag_results in yml["Diagnostics"]:
            # print(diag_results)
            diag = TidyDiagnostic(diag_results["DiagnosticName"])
            diag.message = diag_results["DiagnosticMessage"]["Message"]
            line_cnt, cols = get_line_cnt_from_cols(
                yml["MainSourceFile"], diag_results["DiagnosticMessage"]["FileOffset"]
            )
            diag.line, diag.cols = (line_cnt, cols)
            for replacement in diag_results["DiagnosticMessage"]["Replacements"]:
                line_cnt, cols = get_line_cnt_from_cols(
                    yml["MainSourceFile"], replacement["Offset"]
                )
                fix = TidyReplacement(line_cnt, cols, replacement["Length"])
                fix.text = bytes(replacement["ReplacementText"], encoding="utf-8")
                diag.replacements.append(fix)
            fixit.diagnostics.append(diag)
        GlobalParser.advice.append(fixit)

    # print results
    for j, fix in enumerate(GlobalParser.advice):
        if isinstance(fix, YMLFixin):
            for i, diag in enumerate(fix.diagnostics):
                # filter out absolute header gaurds
                if diag.message.startswith("header is missing header guard"):
                    print("filtering header guard suggestion (making relative to repo root)")
                    GlobalParser.advice[j].diagnostics[i].replacements[0].text = diag.replacements[0].text.replace(
                        CWD_HEADER_GAURD, b""
                    )
                # print(
                #     f"diagnostic name: {diag.name}\n    message: {diag.message}\n"
                #     f"    @ line {diag.line} cols: {diag.cols}"
                # )
                # for replac in diag.replacements:
                #     print(
                #         f"    replace @ line {replac.line} cols {replac.cols} "
                #         f"for length {replac.null_len} of original\n"
                #         f"\treplace text: {replac.text}"
                #     )


if __name__ == "__main__":
    parse_tidy_suggestions_yml()
