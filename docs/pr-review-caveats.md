# Pull Request Review Caveats

[repository settings]: https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/enabling-features-for-your-repository/managing-github-actions-settings-for-a-repository#preventing-github-actions-from-creating-or-approving-pull-requests
[organization settings]: https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/enabling-features-for-your-repository/managing-github-actions-settings-for-a-repository#preventing-github-actions-from-creating-or-approving-pull-requests
[hiding a comment]: https://docs.github.com/en/communities/moderating-comments-and-conversations/managing-disruptive-comments#hiding-a-comment
[resolve a conversion]: https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/reviewing-changes-in-pull-requests/commenting-on-a-pull-request#resolving-conversations

[tidy-review]: inputs-outputs.md#tidy-review
[format-review]: inputs-outputs.md#format-review
[lines-changed-only]: inputs-outputs.md#lines-changed-only
[style]: inputs-outputs.md#style

!!! abstract
    This information is specific to GitHub Pull Requests (often abbreviated as "PR").

While the Pull Request review feature has been diligently tested, there are still some caveats to
beware of when using Pull Request reviews.

## Bot Permissions required
The "GitHub Actions" bot may need to be allowed to approve Pull Requests.
By default, the bot cannot approve Pull Request changes, only request more changes.
This will show as a warning in the workflow logs if the given token (set to the
environment variable `GITHUB_TOKEN`) isn't configured with the proper permissions.

!!! note "See also"
    Refer to the GitHub documentation for [repository settings][] or [organization settings][]
    about adjusting the required permissions for GitHub Actions's `secrets.GITHUB_TOKEN`.

    See our [documented permissions](permissions.md#pull-request-reviews).

## Auto-disabled for certain event types
The feature is auto-disabled for

- closed Pull Requests
- Pull Requests marked as "draft"
- push events

## Posts a new review on each run
Clang-tidy and clang-format suggestions are shown in 1 Pull Request review.

- Users are encouraged to choose either [`tidy-review`][tidy-review] or [`format-review`][format-review].
  Enabling both will likely show duplicate or similar suggestions.
  Remember, clang-tidy can be configured to use the same [`style`][style] that clang-format accepts.
  There is no current implementation to combine suggestions from both tools (clang-tidy kind of
  does that anyway).
- Each generated review is specific to the commit that triggered the Continuous Integration
  workflow.
- Outdated reviews are dismissed but not marked as resolved.
  Also, the outdated review's summary comment is not automatically hidden.
  To reduce the Pull Request's thread noise, users interaction is required.

!!! note "See also"
    Refer to GitHub's documentation about [hiding a comment][].
    Hiding a Pull Request review's summary comment will not resolve the suggestions in the diff.
    Please also refer to [resolve a conversion][] to collapse outdated or duplicate suggestions
    in the diff.

GitHub REST API does not provide a way to hide comments or mark review suggestions as resolved.

!!! tip
    We do support an environment variable named `CPP_LINTER_PR_REVIEW_SUMMARY_ONLY`.
    If the variable is set to ``true``, then the review only contains a summary comment
    with no suggestions posted in the diff.

## Probable non-exhaustive reviews
If any suggestions did not fit within the Pull Request diff, then the review's summary comment will
indicate how many suggestions were left out.
The full patch of suggestions is always included as a collapsed code block in the review summary
comment. This isn't a problem we can fix.
GitHub won't allow review comments/suggestions to target lines that are not shown in the Pull
Request diff (the summation of file differences in a Pull Request).

- Users are encouraged to set [`lines-changed-only`][lines-changed-only] to `true`.
  This will *help* us keep the suggestions limited to lines that are shown within the Pull
  Request diff.
  However, there are still some cases where clang-format or clang-tidy will apply fixes to lines
  that are not within the diff.
  This can't be avoided because the `--line-filter` passed to the clang-tidy (and `--lines`
  passed to clang-format) only applies to analysis, not fixes.
- Not every diagnostic from clang-tidy can be automatically fixed.
  Some diagnostics require user interaction/decision to properly address.
- Some fixes provided might depend on what compiler is used.
  We have made it so clang-tidy takes advantage of any fixes provided by the compiler.
  Compilation errors may still prevent clang-tidy from reporting all concerns.
