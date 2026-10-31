---
title: Format check
description: A one-step GitHub Action that fails a pull request or push when the C/C++ lines it changes are not clang-formatted.
---

# Format check

`cpp-linter/cpp-linter-action/format` checks that the C/C++ lines a pull request or push
changes follow clang-format, and fails the job when they do not. It is a separate, smaller
action in this repository: one step, no token, no Python.

```yaml
name: cpp-linter
on:
  pull_request:
  push:
    branches: [main]

jobs:
  format:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
      - uses: cpp-linter/cpp-linter-action/format@v2
```

## What it does

1. Downloads the newest patch release of the clang-format major you ask for (21 by default)
   from [cpp-linter/clang-tools-static-binaries], and checks its SHA-512.
2. Works out what changed:
    - `pull_request`: the merge commit that `actions/checkout` checks out, compared with its
      first parent (the base branch).
    - `push`: the pushed commits, compared with the commit before the push (for a new branch,
      with the parent of the last commit).
    - `merge_group`: the merge queue's base commit.
    - Any other event, such as `workflow_dispatch` or `schedule`: every file.

    The base commit is fetched on its own, so the default `fetch-depth: 1` of
    `actions/checkout` is enough.
3. Runs `clang-format --dry-run --Werror` on the changed lines of each changed file.
4. For every line that is not formatted, adds an error annotation, which shows in the pull
   request's diff view. The step summary lists the files and shows the change clang-format
   would make; the job log has the full diff.
5. Fails the step when any file needs formatting.

Lines the change does not touch are not checked, so an old code base can turn the check on
without reformatting everything first.

## Inputs

| Input | Default | Description |
|---|---|---|
| `version` | `21` | clang-format major version, from 12 to 23. |
| `style` | `file` | Passed to `clang-format --style`. `file` uses the closest `.clang-format`, and LLVM style when there is none. Any built-in style (`google`, `webkit`, ...) works too. |
| `extensions` | `c,h,C,H,cpp,hpp,cc,hh,c++,h++,cxx,hxx` | File extensions to check, comma-separated. |
| `ignore` | (none) | Paths to skip, separated by `\|` or new lines, as git pathspecs relative to the repository root. `build` skips the `build` directory, `*.pb.cc` skips matching files anywhere. |
| `files-changed-only` | `true` | Check only the files the pull request or push changes. `false` checks every tracked file with a matching extension. |
| `lines-changed-only` | `true` | Check only the added or changed lines. `false` checks the whole of each changed file. |

Files listed in a [`.clang-format-ignore`][clang-format-ignore] file are skipped too, with
clang-format 18 or later.

## Outputs

| Output | Description |
|---|---|
| `checks-failed` | The number of files with style issues. |
| `clang-format-version` | The full clang-format version used, for example `21.1.8`. |

The step fails when `checks-failed` is not 0. To report without failing, set
`continue-on-error: true` on the step.

## Moving from another clang-format action

Those actions check the whole repository by default. To get the same, set
`files-changed-only: false`; to check only what each pull request changes, keep the default.

| [DoozyX/clang-format-lint-action] | This action |
|---|---|
| `clangFormatVersion: 18` | `version: 18` (12 to 23) |
| `style: file` | `style: file` (the default) |
| `extensions: 'h,cpp'` | `extensions: 'h,cpp'` |
| `exclude` (paths to skip) | `ignore`, with paths separated by `\|` or new lines |
| `source: './src'` | not needed; use `ignore` for paths to skip |
| `inplace: True` | use the main action's [`auto-fix`](inputs-outputs.md#auto-fix) |

| [jidicula/clang-format-action] | This action |
|---|---|
| `clang-format-version: '22'` | `version: '22'` (12 to 23) |
| `check-path: 'src'` | not needed; use `ignore` for paths to skip |
| `exclude-regex: '^./third_party/.*$'` | `ignore: 'third_party'` (a pathspec, not a regex) |
| `include-regex` | `extensions` (a list of extensions, not a regex) |

## Runners and limits

- GitHub-hosted Linux (x64, arm64), macOS and Windows runners work. Self-hosted runners and
  `container:` jobs need `bash`, `git`, `curl` and `jq`.
- It only reports. For review suggestions, a pull request comment, auto-fix or clang-tidy,
  use the [main action](index.md).
- `--style=file` reads `.clang-format` files from the checked-out pull request, as
  clang-format does locally.

[cpp-linter/clang-tools-static-binaries]: https://github.com/cpp-linter/clang-tools-static-binaries
[clang-format-ignore]: https://clang.llvm.org/docs/ClangFormat.html#clang-format-ignore
[DoozyX/clang-format-lint-action]: https://github.com/DoozyX/clang-format-lint-action
[jidicula/clang-format-action]: https://github.com/jidicula/clang-format-action
