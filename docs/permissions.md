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

!!! info "The action checks out the pull request head"

    On `pull_request` events `actions/checkout` provides the merge commit
    (`refs/pull/N/merge`), not the branch. A commit made on it would carry that
    merge into the pull request, so with `auto-fix` the action checks out the
    pull request's head commit before it lints. Steps that run after the action
    see that commit plus the auto-fix commit. If git refuses the checkout
    because of local changes, auto-fix is skipped with a warning.

!!! warning "Limits"

    Commits pushed with the default `GITHUB_TOKEN` do not start new workflow
    runs, so CI does not re-check the auto-fix commit. To change that, push
    with a [GitHub App token](#github-app-token) or a personal access token
    that has `contents: write`; add `[skip ci]` to
    [`auto-fix-commit-msg`](./inputs-outputs.md#auto-fix-commit-msg) if a
    particular auto-fix commit should not start a run.

    Pull requests from forks are skipped with a warning: `GITHUB_TOKEN` cannot
    push to the fork's branch, and fork pull requests receive no secrets, so an
    App token or PAT is not available there either. They are skipped on
    `pull_request_target` as well, where the token could push, but only to this
    repository.

## GitHub App token

A token minted from a GitHub App you own replaces the default `GITHUB_TOKEN`
for every feature on this page. Pushes made with it start workflow runs, and
comments and reviews are posted under the App's name instead of
`github-actions[bot]`.

1. [Register a GitHub App](https://docs.github.com/en/apps/creating-github-apps/registering-a-github-app/registering-a-github-app)
   with the repository permissions **Contents: Read and write** and
   **Pull requests: Read and write**, then install it on the repository.
2. Store the App ID as a repository variable and the private key as a secret.
3. Mint the token at the start of the job and pass it to both `actions/checkout`
   and cpp-linter:

```yaml
    steps:
      - uses: actions/create-github-app-token@v3
        id: app-token
        with:
          app-id: ${{ vars.CPP_LINTER_APP_ID }}
          private-key: ${{ secrets.CPP_LINTER_APP_PRIVATE_KEY }}
      - uses: actions/checkout@v7
        with:
          token: ${{ steps.app-token.outputs.token }} # (1)!
      - uses: cpp-linter/cpp-linter-action@v2
        env:
          GITHUB_TOKEN: ${{ steps.app-token.outputs.token }} # (2)!
        with:
          style: 'file'
          auto-fix: 'true'
```

1. The auto-fix commit is pushed with this token, so the push triggers your
   other workflows.
2. Thread comments and pull request reviews are posted with this token.

The job's `permissions` block only applies to `GITHUB_TOKEN`; the App token's
permissions come from the App's settings.
