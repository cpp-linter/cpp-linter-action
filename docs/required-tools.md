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

## Where clang tools come from

The `version` input is resolved on every runner by trying these sources in order
(whichever succeeds first):

1. A `clang-format`/`clang-tidy` already installed on the runner whose version satisfies `version`.
2. A version that cpp-linter downloaded earlier and kept in its cache.
3. The system package manager:
    - Linux: `apt` (falling back to LLVM's official apt repository), `dnf`, `pacman`, or Homebrew
    - macOS: Homebrew
    - Windows: Chocolatey or winget
4. PyPI packages [clang-tidy][clang-tidy-wheel] and/or [clang-format][clang-format-wheel]
5. Static binaries that we build ourselves; see the [cpp-linter/clang-tools-static-binaries] project.

[nushell]: https://www.nushell.sh/
[uv]: https://docs.astral.sh/uv/
[cpp-linter/clang-tools-static-binaries]: https://github.com/cpp-linter/clang-tools-static-binaries
[gh-container-syntax]: https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#jobsjob_idcontainer
[clang-tidy-wheel]: https://pypi.org/project/clang-tidy
[clang-format-wheel]: https://pypi.org/project/clang-format
