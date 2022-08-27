<!--intro-start-->

# C/C++ Lint Action <sub><sup>| clang-format & clang-tidy</sup></sub>

![GitHub release (latest SemVer)](https://img.shields.io/github/v/release/cpp-linter/cpp-linter-action?style=flat-square)
[![GitHub marketplace](https://img.shields.io/badge/marketplace-C%2FC%2B%2B%20Lint%20Action-blue?logo=github&style=flat-square)](https://github.com/marketplace/actions/c-c-lint-action)
[![GitHub Workflow Status](https://img.shields.io/github/workflow/status/cpp-linter/cpp-linter-action/cpp-linter?label=cpp-linter&logo=Github&style=flat-square)](https://github.com/cpp-linter/cpp-linter-action/actions/workflows/cpp-linter.yml)
[![GitHub Workflow Status](https://img.shields.io/github/workflow/status/cpp-linter/cpp-linter-action/MkDocs%20Deploy?label=docs&logo=Github&style=flat-square)](https://github.com/cpp-linter/cpp-linter-action/actions/workflows/mkdocs-deploy.yml)
![GitHub](https://img.shields.io/github/license/cpp-linter/cpp-linter-action?label=license&logo=github&style=flat-square)
[![codecov](https://codecov.io/gh/cpp-linter/cpp-linter-action/branch/master/graph/badge.svg?token=4SF7UEDEZ2)](https://codecov.io/gh/cpp-linter/cpp-linter-action)

A Github Action for linting C/C++ code integrating clang-tidy and clang-format to collect feedback provided in the form of thread comments and/or annotations.

## Usage

Create a new GitHub Actions workflow in your project, e.g. at [.github/workflows/cpp-linter.yml](https://github.com/cpp-linter/cpp-linter-action/blob/master/.github/workflows/cpp-linter.yml)

The content of the file should be in the following format.

```yaml
# Workflow syntax:
# https://help.github.com/en/articles/workflow-syntax-for-github-actions
name: cpp-linter

on:
  pull_request:
    types: [opened, reopened]  # let PR-synchronize events be handled by push events
  push:

jobs:
  cpp-linter:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: cpp-linter/cpp-linter-action@v1
        id: linter
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        with:
          style: file

      - name: Fail fast?!
        if: steps.linter.outputs.checks-failed > 0
        run: echo "Some files failed the linting checks!"
        # for actual deployment
        # run: exit 1
```

### Optional Inputs

#### `style`

- **Description**: The style rules to use.
  - Set this to 'file' to have clang-format use the closest relative .clang-format file.
  - Set this to a blank string (`''`) to disable the use of clang-format entirely.
- Default: 'llvm'

#### `extensions`

- **Description**: The file extensions to run the action against. This is a comma-separated string.
- Default: 'c,h,C,H,cpp,hpp,cc,hh,c++,h++,cxx,hxx'

#### `tidy-checks`

- **Description**: Comma-separated list of globs with optional `-` prefix. Globs are processed in order of appearance in the list. Globs without `-` prefix add checks with matching names to the set, globs with the `-` prefix remove checks with matching names from the set of enabled checks. This option's value is appended to the value of the 'Checks' option in a .clang-tidy file (if any).
    - It is possible to disable clang-tidy entirely by setting this option to `'-*'`.
    - It is also possible to rely solely on a .clang-tidy config file by specifying this option as a blank string (`''`).
- Default: 'boost-\*,bugprone-\*,performance-\*,readability-\*,portability-\*,modernize-\*,clang-analyzer-\*,cppcoreguidelines-\*'

#### `repo-root`

- **Description**: The relative path to the repository root directory. This path is relative to the path designated as the runner's GITHUB_WORKSPACE environment variable.
- Default: '.'

#### `version`

- **Description**: The desired version of the [clang-tools](https://github.com/cpp-linter/clang-tools-pip) to use. Accepted options are strings which can be 14, 13, 12, 11, 10, 9, 8，7, 6, 5, 4 or 3.9.
    - Set this option to a blank string (`''`) to use the platform's default installed version.
    - This value can also be a path to where the clang tools are installed (if using a custom install location).
- Default: '12'

#### `verbosity`

- **Description**: This controls the action's verbosity in the workflow's logs. Supported options are defined by the [python logging library's log levels](https://docs.python.org/3/library/logging.html#logging-levels). This option does not affect the verbosity of resulting thread comments or file annotations.
- Default: '10'

#### `lines-changed-only`

- **Description**: This controls what part of the files are analyzed. The following values are accepted:
    - false: All lines in a file are analyzed.
    - true: Only lines in the diff that contain additions are analyzed.
    - diff: All lines in the diff are analyzed (including unchanged lines but not subtractions).
- Default: false.

#### `files-changed-only`

- **Description**: Set this option to false to analyze any source files in the repo. This is automatically enabled if lines-changed-only is enabled.
- Default: true
- NOTE: The `GITHUB_TOKEN` should be supplied when running on a private repository with this option enabled, otherwise the runner does not not have the privilege to list changed files for an event. See [Authenticating with the GITHUB_TOKEN](https://docs.github.com/en/actions/reference/authentication-in-a-workflow)

#### `ignore`

- **Description**: Set this option with string of path(s) to ignore.
  - In the case of multiple paths, you can use a pipe character (`|`)
    to separate the multiple paths. Multiple lines are forbidden as an input to this option; it must be a single string.
  - This can also have files, but the file's relative path has to be specified
    as well.
  - There is no need to use `./` for each entry; a blank string (`''`) represents
    the repo-root path (specified by the `repo-root` input option).
  - Submodules are automatically ignored. Hidden directories (beginning with a `.`) are also ignored automatically.
  - Prefix a path with a bang (`!`) to make it explicitly _not_ ignored. The order of
    multiple paths does _not_ take precedence. The `!` prefix can be applied to
    a submodule's path (if desired) but not hidden directories.
  - Glob patterns are not supported here. All asterisk characters (`*`) are literal.
- Default: '.github'

#### `thread-comments`

- **Description**: Set this option to false to disable the use of thread comments as feedback.
  - To use thread comments, the `GITHUB_TOKEN` (provided by Github to each repository) must be declared as an environment
    variable. See [Authenticating with the GITHUB_TOKEN](https://docs.github.com/en/actions/reference/authentication-in-a-workflow)
- Default: false
- NOTE: If run on a private repository, then this feature is disabled because the GitHub REST API behaves differently for thread comments on a private repository.

#### `file-annotations`

- **Description**: Set this option to false to disable the use of file annotations as feedback.
- Default: true

#### `database`

- **Description**: The directory containing compilation database (like compile_commands.json) file.
- Default: ''

### Outputs

This action creates 1 output variable named `checks-failed`. Even if the linting checks fail for source files this action will still pass, but users' CI workflows can use this action's output to exit the workflow early if that is desired.

## Example

<!--intro-end-->

### Annotations

![clang-format annotations](https://raw.githubusercontent.com/cpp-linter/cpp-linter-action/master/docs/images/annotations-clang-format.png)

![clang-tidy annotations](https://raw.githubusercontent.com/cpp-linter/cpp-linter-action/master/docs/images/annotations-clang-tidy.png)

### Thread Comment

![sample comment](https://raw.githubusercontent.com/cpp-linter/cpp-linter-action/master/docs/images/comment.png)

<!--footer-start-->

## Add C/C++ Lint Action badge in README

You can show C/C++ Lint Action status with a badge in your repository README

Example

```markdown
[![cpp-linter](https://github.com/cpp-linter/cpp-linter-action/actions/workflows/cpp-linter.yml/badge.svg)](https://github.com/cpp-linter/cpp-linter-action/actions/workflows/cpp-linter.yml)
```

[![cpp-linter](https://github.com/cpp-linter/cpp-linter-action/actions/workflows/cpp-linter.yml/badge.svg)](https://github.com/cpp-linter/cpp-linter-action/actions/workflows/cpp-linter.yml)

## Have question or feedback?

To provide feedback (requesting a feature or reporting a bug) please post to [issues](https://github.com/cpp-linter/cpp-linter-action/issues).

## License

The scripts and documentation in this project are released under the [MIT License](https://github.com/cpp-linter/cpp-linter-action/blob/master/LICENSE)

<!--footer-end-->
