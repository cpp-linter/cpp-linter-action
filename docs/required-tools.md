# Required Tools

As of v2.16.0, this action uses

- [nushell] for cross-platform compatible scripting
- [uv] for driving a Python virtual environment

This action installs [nushell] and [uv] automatically.
Only [nushell] is added to the PATH environment variable.
[uv], and any standalone Python distribution it downloads, are not added to the PATH environment variable.

## On Linux runners

We only support Linux runners using a Debian-based Linux OS (like Ubuntu and many others).
This is because we first try to use the `apt` package manager to install clang tools.

Linux workflows that use a specific [`container`][gh-container-syntax] should ensure that
the following are installed:

- GLIBC (v2.32 or later)
- `wget` or `curl`
- `lsb-release` (required by LLVM-provided install script)
- `software-properties-common` (required by LLVM-provided install script)
- `gnupg` (required by LLVM-provided install script)

```shell
apt-get update
apt-get install -y libc6 wget lsb-release software-properties-common gnupg
```

Otherwise, [nushell] and/or the LLVM-provided bash script will fail to run.

If installing clang tools fails using the `apt` package manager, then
we alternatively try the following sources in order:

1. Static binaries that we built ourselves; see [cpp-linter/clang-tools-pip] project for more detail.
2. PyPI Packages [clang-tidy][clang-tidy-wheel] and/or [clang-format][clang-format-wheel]

## On macOS runners

The specified `version` of `clang-format` and `clang-tidy` is installed via
the following sources in order (whichever succeeds first):

1. Homebrew
2. Static binaries that we built ourselves; see [cpp-linter/clang-tools-pip] project for more detail.
3. PyPI Packages [clang-tidy][clang-tidy-wheel] and/or [clang-format][clang-format-wheel]

## On Windows runners

For Windows runners, we use clang tools installed via
the following sources in order (whichever succeeds first):

1. Static binaries that we built ourselves; see [cpp-linter/clang-tools-pip] project for more detail.
2. PyPI Packages [clang-tidy][clang-tidy-wheel] and/or [clang-format][clang-format-wheel]

[nushell]: https://www.nushell.sh/
[uv]: https://docs.astral.sh/uv/
[cpp-linter/clang-tools-pip]: https://github.com/cpp-linter/clang-tools-pip
[gh-container-syntax]: https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#jobsjob_idcontainer
[clang-tidy-wheel]: https://pypi.org/project/clang-tidy
[clang-format-wheel]: https://pypi.org/project/clang-format
