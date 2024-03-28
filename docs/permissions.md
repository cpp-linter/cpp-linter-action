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

The [`tidy-review`](inputs-outputs.md#tidy-review) and [`format-review`](inputs-outputs.md#format-review) features require the following permissions:

```yaml
    permissions:
      pull-requests: write
```
