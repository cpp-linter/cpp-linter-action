# Token Permissions

This is an exhaustive list of required permissions organized by features.

!!! info "Important"
    The `GITHUB_TOKEN` environment variable should be supplied when running on a private repository.
    Otherwise the runner does not not have the privileges needed for the features mentioned here.

    See also [Authenticating with the `GITHUB_TOKEN`](https://docs.github.com/en/actions/reference/authentication-in-a-workflow)

## File Changes

When using [`files-changed-only`](inputs-outputs.md#files-changed-only) or
[`lines-changed-only`](inputs-outputs.md#lines-changed-only) to get the list
of file changes for a CI event, the following permissions are needed:

=== "`#!yaml on: push`"

    For [push events](https://docs.github.com/en/actions/using-workflows/events-that-trigger-workflows#push)

    ```yaml
        permissions:
          contents: read # (1)!
    ```

    1. This permission is also needed to download files if the repository is not
       checked out before running cpp-linter.

=== "`#!yaml on: pull_request`"

    For [pull_request events](https://docs.github.com/en/actions/using-workflows/events-that-trigger-workflows#pull_request)

    ```yaml
        permissions:
          contents: read # (1)!
          pull-requests: read # (2)!
    ```

    1. For pull requests, this permission is only needed to download files if
       the repository is not checked out before running cpp-linter.
    2. Specifying `#!yaml write` is also sufficient as that is required for

        * posting [thread comments](#thread-comments) on pull requests
        * posting [pull request reviews](#pull-request-reviews)

## Thread Comments

The [`thread-comments`](inputs-outputs.md#thread-comments) feature requires the following permissions:

=== "`#!yaml on: push`"

    For [push events](https://docs.github.com/en/actions/using-workflows/events-that-trigger-workflows#push)

    ```yaml
        permissions:
          metadata: read # (1)!
          contents: write # (2)!
    ```

    1. needed to fetch existing comments
    2. needed to post or update a commit comment. This also allows us to delete
       an outdated comment if needed.

=== "`#!yaml on: pull_request`"

    For [pull_request events](https://docs.github.com/en/actions/using-workflows/events-that-trigger-workflows#pull_request)

    ```yaml
        permissions:
          pull-requests: write
    ```

## Pull Request Reviews

The [`tidy-review`](inputs-outputs.md#tidy-review), [`format-review`](inputs-outputs.md#format-review), and [`passive-reviews`](inputs-outputs.md#passive-reviews) features require the following permissions:

```yaml
    permissions:
      pull-requests: write
```

## Auto-fix

The [`auto-fix`](inputs-outputs.md#auto-fix) feature requires `contents: write` permission
in addition to any other permissions needed for other features:

```yaml
    permissions:
      contents: write # (1)!
```

1. Needed by the token used in `actions/checkout` to commit and push the
   formatted changes back to the branch.

!!! warning "CI re-triggering with auto-fix"

    The default `GITHUB_TOKEN` **cannot** trigger new CI runs when pushing
    a commit. If you need the auto-fix commit to trigger CI checks
    (e.g. to verify the fix builds clean), use a personal access token
    (PAT) with `contents: write` scope on the checkout step:

    ```yaml
    - uses: actions/checkout@v7
      with:
        token: ${{ secrets.MY_PAT }}
    ```

    Conversely, if you use a PAT or GitHub App token (whose pushes **do**
    trigger CI) but do not want the auto-fix commit itself to start a new
    run, include `[skip ci]` in the commit message via the
    [`auto-fix-commit-msg`](./inputs-outputs.md#auto-fix-commit-msg) input.
    With the default `GITHUB_TOKEN`, `[skip ci]` is unnecessary since the
    push does not trigger CI anyway.

!!! warning "Pull requests from third-party forks"

    Auto-fix is automatically skipped for pull requests from third-party
    forks: the `GITHUB_TOKEN` cannot push to the fork's branch, so the
    action emits a warning and makes no commit. Use `auto-fix` on `push`
    events or on pull requests from the same repository.
