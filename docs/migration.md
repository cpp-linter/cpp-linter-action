---
title: Migrating to v3
description: What changes when a workflow moves from cpp-linter-action v2 (or v1) to v3, and what to edit.
---

<!-- markdownlint-disable MD041 -->

[version]: inputs-outputs.md#version
[pr-review]: inputs-outputs.md#pr-review
[tidy-review]: inputs-outputs.md#tidy-review
[format-review]: inputs-outputs.md#format-review
[jobs]: inputs-outputs.md#jobs
[auto-fix]: inputs-outputs.md#auto-fix
[auto-fix-commit-msg]: inputs-outputs.md#auto-fix-commit-msg
[fix-patch-path]: inputs-outputs.md#fix-patch-path
[tidy-checks]: inputs-outputs.md#tidy-checks
[lines-changed-only]: inputs-outputs.md#lines-changed-only
[verbosity]: inputs-outputs.md#verbosity
[style]: inputs-outputs.md#style
[sarif-file]: inputs-outputs.md#sarif-file
[strict]: inputs-outputs.md#strict
[checks-failed]: inputs-outputs.md#checks-failed
[cli-migration]: https://cpp-linter.github.io/cpp-linter-rs/migration/

# Migrating to v3

cpp-linter-action v3 runs cpp-linter v2, a rewrite in Rust. v2 of this action runs cpp-linter v1
(Python). Most inputs keep their names and meaning, and no output was removed, so many workflows
only need `@v2` changed to `@v3`. This page lists the inputs that changed and the behavior that
differs. For the changes in cpp-linter itself, see [Migrating from v1][cli-migration] in the
cpp-linter docs.

Workflows that use `@v2` keep working as they are. v2 gets bug and security fixes only, and new
features go into v3.

## Upgrade in one step

```diff
-      - uses: cpp-linter/cpp-linter-action@v2
+      - uses: cpp-linter/cpp-linter-action@v3
         id: linter
         env:
           GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
         with:
           style: file
           tidy-checks: ''
-          format-review: true
+          pr-review: true
```

Then check the sections below for the inputs your workflow sets.

## Renamed or merged inputs

| v2 input | v3 input | Notes |
|---|---|---|
| [`tidy-review`][tidy-review] | [`pr-review`][pr-review] | v3 posts one review with suggestions from both clang-tidy and clang-format. `tidy-review` still works as an alias of `pr-review`, so `tidy-review: true` now also adds clang-format suggestions. |
| [`format-review`][format-review] | [`pr-review`][pr-review] | Same as above. `format-review: true` now also adds clang-tidy suggestions. |

The old names can still be given together. Reviews are enabled if any of them is `true`.

## Deprecated inputs

| v2 input | v3 behavior | What to do |
|---|---|---|
| [`jobs`][jobs] | Files are always analyzed in parallel. The value is ignored with a deprecation warning. | Remove the input. |

## New inputs

| Input | What it does |
|---|---|
| [`strict`][strict] | `true` fails the step when any check fails. The outputs are still set, so a step that reads [`checks-failed`][checks-failed] only to fail the job can be removed. |
| [`sarif-file`][sarif-file] | Writes the clang-tidy findings to a SARIF file. Upload it with `github/codeql-action/upload-sarif` to see them in the Security tab. See the "GitHub code scanning" [recipe](examples/index.md). |

## Changed defaults

| Input | v2 default | v3 default |
|---|---|---|
| [`version`][version] | `21` | `latest`, the newest major version that cpp-linter can install (23 with cpp-linter 2.0) |
| [`auto-fix-commit-msg`][auto-fix-commit-msg] | `style: apply clang-format fixes` | `style: apply clang-format and clang-tidy fixes` |

With `latest`, the clang tools move to a new major version when a cpp-linter release adds one, and
a new major version can report new findings. To keep the results stable, set
[`version`][version] to a major version, such as `version: 21`.

## Clang tools are installed for you

v2 installs the clang tools from [clang-tools-pip](https://github.com/cpp-linter/clang-tools-pip)
before it runs, and [`version`][version] takes a major version from 12 to 23.

In v3, cpp-linter installs the tools itself, and only the ones it needs for the files it found.
[`version`][version] also takes a version requirement, such as `18.1.8`, `=18.1.8` or `>=17, <20`.
If no matching tools are installed, v3 tries the runner's package manager first, then PyPI wheels,
then the static binaries built by cpp-linter. A blank string still uses the installed tools, and a
path still points to a custom install location.

## Fixes include clang-tidy

In v2, [`auto-fix`][auto-fix] commits clang-format fixes only.

In v3, it commits one patch with the fixes from clang-format and clang-tidy. The same patch is set
as the new [`fix-patch-path`][fix-patch-path] output, so a workflow can also upload it or apply it
in a later step. clang-tidy fixes can change what the code does, so review the commit. To commit
only clang-format fixes, disable clang-tidy with [`tidy-checks: '-*'`][tidy-checks].

## Errors that v2 ignored

- An invalid [`lines-changed-only`][lines-changed-only] or [`version`][version] value now fails the
  step with exit code 2. v2 treated it as `false` or kept going.
- When clang-format exits with an error for a file, for example because of a bad [`style`][style]
  or a `.clang-format` key that the installed version does not know, v3 logs a warning and counts
  the file in `clang-format-checks-failed`. If clang-format fails on every file, the step fails.
  v2 counted such a file as formatted.

## Outputs

`checks-failed`, `clang-tidy-checks-failed` and `clang-format-checks-failed` are unchanged. v3 adds
[`fix-patch-path`][fix-patch-path].

## From v1

v1 runs in a Docker container, and v3 runs on the runner itself, so it also works on macOS and
Windows runners. On top of the changes above:

- [`verbosity`][verbosity] takes `info` or `debug` instead of a Python logging level. Replace
  `10` (the v1 default) with `debug`, and `20` with `info`.
- The [`version`][version] default was `12` in v1.
