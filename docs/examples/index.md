
[style]: ../inputs-outputs.md#style
[tidy-checks]: ../inputs-outputs.md#tidy-checks
[thread-comments]: ../inputs-outputs.md#thread-comments
[auto-fix]: ../inputs-outputs.md#auto-fix
[summary-output-file]: ../inputs-outputs.md#summary-output-file

# Recipes

Here are some example workflows to get started quickly.

=== "auto-fix clang-format"

    ``` yaml
    --8<-- ".github/workflows/examples/auto-fix.yml"
    ```

    1. See also [`auto-fix`][auto-fix]
    2. See also [`style`][style]
    3. See also [`tidy-checks`][tidy-checks]

=== "only clang-tidy"

    ``` yaml
    --8<-- ".github/workflows/examples/only-clang-tidy.yml"
    ```

    1. See also [`style`][style]
    2. See also [`tidy-checks`][tidy-checks]

=== "only clang-format"

    ``` yaml
    --8<-- ".github/workflows/examples/only-clang-format.yml"
    ```

    1. See also [`style`][style]
    2. See also [`tidy-checks`][tidy-checks]

=== "only PR comments"

    ``` yaml
    --8<-- ".github/workflows/examples/only-PR-comments.yml"
    ```

    1. See also our [token permissions document](../permissions.md)
    2. See also [`style`][style]
    3. See also [`tidy-checks`][tidy-checks]
    4. See also [`thread-comments`][thread-comments]

=== "PR comments from forks"

    The token of a pull request from a fork is read-only, so the action cannot comment
    there. Split the work into two workflows: the first lints with a read-only token and
    uploads the comment as an artifact; the second runs on `workflow_run` with
    `pull-requests: write` and posts it. See [pull requests from forks](../permissions.md#pull-requests-from-forks).

    `.github/workflows/cpp-linter.yml`

    ``` yaml
    --8<-- ".github/workflows/examples/fork-PR-comments-lint.yml"
    ```

    1. The second workflow finds this one by its `name`.
    2. Read-only, as for any pull request from a fork.
    3. See also [`style`][style]
    4. See also [`tidy-checks`][tidy-checks]
    5. See also [`thread-comments`][thread-comments] and [`summary-output-file`][summary-output-file]

    `.github/workflows/cpp-linter-comment.yml`

    ``` yaml
    --8<-- ".github/workflows/examples/fork-PR-comments-post.yml"
    ```

    1. Must match the `name` of the first workflow. GitHub runs this workflow from the
       default branch only, so it takes effect after it is merged there.
    2. Needed to download the artifact of the first workflow's run.
    3. This workflow has a write token, so it must not check out or run anything from the
       pull request. It only reads two files from the artifact.
    4. Anyone who opens a pull request can change the first workflow and so the artifact.
       The pull request number in it is checked against the commit and the fork that the
       first workflow linted.
