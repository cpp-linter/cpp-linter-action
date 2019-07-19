# Clang Tidy Action

[![License](https://img.shields.io/badge/License-BSD%203--Clause-blue.svg)](https://opensource.org/licenses/BSD-3-Clause)

A GitHub action to automatically execute a Clang Tidy linter on C/C++ files changed in a pull request.

## Usage

```
workflow "on pull request, lint with clang-tidy " {
  on = "pull_request"
  resolves = ["clang-tidy"]
}

action "clang-tidy" {
  uses = "muxee/clang-tidy-action@master"
  secrets = ["GITHUB_TOKEN"]

  args = "-checks=*"
}

```

Please see the [official documentation](https://clang.llvm.org/extra/clang-tidy) for more information
