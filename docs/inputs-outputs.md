# Inputs and Outputs

These are the action inputs and outputs offered by cpp-linter-action.

## Inputs

### `style`

<!-- md:version 1.2.0 -->
<!-- md:default 'llvm' -->

The style rules to use.

- Set this to 'file' to have clang-format use the closest relative .clang-format file.
- Set this to a blank string (`''`) to disable the use of clang-format entirely.
- Any code style supported by the specified version of clang-format.

### `extensions`

<!-- md:version 1.2.0 -->
<!-- md:default 'c,h,C,H,cpp,hpp,cc,hh,c++,h++,cxx,hxx' -->

The file extensions to run the action against. This is a comma-separated string.

### `tidy-checks`

<!-- md:version 1.2.0 -->
<!-- md:default 'boost-*,bugprone-*,performance-*,readability-*,portability-*,modernize-*,clang-analyzer-*,cppcoreguidelines-*' -->

Comma-separated list of globs with optional `-` prefix. Globs are processed in order of appearance in the list. Globs without `-` prefix add checks with matching names to the set, globs with the `-` prefix remove checks with matching names from the set of enabled checks. This option's value is appended to the value of the 'Checks' option in a .clang-tidy file (if any).
    - It is possible to disable clang-tidy entirely by setting this option to `'-*'`.
    - It is also possible to rely solely on a .clang-tidy config file by specifying this option as a blank string (`''`).

### `repo-root`

<!-- md:version 1.2.0 -->
<!-- md:default '.' -->

The relative path to the repository root directory. This path is relative to the path designated as the runner's `GITHUB_WORKSPACE` environment variable.

### `version`

<!-- md:version 1.2.0 -->
<!-- md:default 12 -->

The desired version of the [clang-tools](https://github.com/cpp-linter/clang-tools-pip) to use. Accepted options are strings which can be 17, 16, 15, 14, 13, 12, 11, 10, 9, 8 or 7.

- Set this option to a blank string (`''`) to use the platform's default installed version.
- This value can also be a path to where the clang tools are installed (if using a custom install location).

### `verbosity`

<!-- md:version 1.3.0 -->
<!-- md:default info -->

This controls the action's verbosity in the workflow's logs. Supported options are `info` or `debug`. This option does not affect the verbosity of resulting thread comments or file annotations.

The verbosity can also be engaged by enabling debug logs when [re-running jobs or workflows](https://docs.github.com/en/actions/managing-workflow-runs/re-running-workflows-and-jobs).

### `lines-changed-only`

<!-- md:version 1.5.0 -->
<!-- md:default false -->
<!-- md:permission content: read #file-changes -->

This controls what part of the files are analyzed. The following values are accepted:

- `false`: All lines in a file are analyzed.
- `true`: Only lines in the diff that contain additions are analyzed.
- `diff`: All lines in the diff are analyzed (including unchanged lines but not subtractions).

!!! info "Important"
    This feature requires special permissions to perform successfully.
    See our [documented permissions](permissions.md)

### `files-changed-only`

<!-- md:version 1.3.0 -->
<!-- md:default true -->
<!-- md:permission content: read #file-changes -->

Set this option to false to analyze any source files in the repo. This is automatically enabled if lines-changed-only is enabled.

!!! info "Important"
    This feature requires special permissions to perform successfully.
    See our [documented permissions](permissions.md)

### `ignore`

<!-- md:version 1.3.0 -->
<!-- md:default .github -->

Set this option with string of path(s) to ignore.

- In the case of multiple paths, you can use a pipe character (`|`)
   to separate the multiple paths. Multiple lines are forbidden as an input to this option; it must be a single string.
- This can also have files, but the file's relative path has to be specified
   as well.
- There is no need to use `./` for each entry; a blank string (`''`) represents
   the repo-root path (specified by the [`repo-root`](#repo-root) input option).
- Submodules are automatically ignored. Hidden directories (beginning with a `.`) are also ignored automatically.
- Prefix a path with a bang (`!`) to make it explicitly _not_ ignored. The order of
   multiple paths does _not_ take precedence. The `!` prefix can be applied to
   a submodule's path (if desired) but not hidden directories.
- Glob patterns are not supported here. All asterisk characters (`*`) are literal.

### `thread-comments`

<!-- md:version 2.6.2 -->
<!-- md:default false -->
<!-- md:permission issues: write #thread-comments -->

This controls the behavior of posted thread comments as feedback. The following options are supported:

- `true`: enable the use of thread comments. This will always delete an outdated thread comment and post a new comment (triggering a notification for every comment).
- `update`: update an existing thread comment if one already exists. This option does not trigger a new notification for every thread comment update.
- `false`: disable the use of thread comments.

!!! info "Important"
    This feature requires special permissions to perform successfully.
    See our [documented permissions](permissions.md)

> [!NOTE]
> If run on a private repository, then this feature is disabled because the GitHub REST API behaves differently for thread comments on a private repository.

### `no-lgtm`

<!-- md:version 2.6.2 -->
<!-- md:default true -->

Set this option to true or false to enable or disable the use of a thread comment or pull request review that basically says 'Looks Good To Me' (when all checks pass).
The default value, `true` means no LGTM comment posted.

See [`thread-comments`](#thread-comments), [`tidy-review`](#tidy-review), and [`format-review`](#format-review) options for further details.

### `step-summary`

<!-- md:version 2.6.0 -->
<!-- md:default false -->

Set this option to true to append content as part of workflow's job summary.

See implementation details in GitHub's documentation about
[Adding a job summary](https://docs.github.com/en/actions/using-workflows/workflow-commands-for-github-actions#adding-a-job-summary).
This option is independent of the [`thread-comments`](#thread-comments) option, rather this option uses the same content that the [`thread-comments`](#thread-comments) option would use.

Note: The [`no-lgtm`](#no-lgtm) option is _not_ applied to step summaries.

### `file-annotations`

<!-- md:version 1.4.3 -->
<!-- md:default true -->

Set this option to `false` to disable the use of file annotations as feedback.

### `database`

<!-- md:version 1.4.0 -->
<!-- md:default '' -->

The directory containing compilation database (like compile_commands.json) file.

### `extra-args`

<!-- md:version 2.1.0 -->
<!-- md:default '' -->

A string of extra arguments passed to clang-tidy for use as compiler arguments (like `-std=c++14 -Wall`).

### `tidy-review`

<!-- md:version 2.9.0 -->
<!-- md:default false -->
<!-- md:flag experimental -->
<!-- md:permission pull_request: write #pull-request-reviews -->

Set this option to `true` to enable Pull Request reviews from clang-tidy.

!!! info "Important"
    This feature requires special permissions to perform successfully.
    See our [documented permissions](permissions.md).

    See also [the PR review feature caveats](pr-review-caveats.md).

> [!NOTE]
> The [`no-lgtm`](#no-lgtm) option is applicable to Pull Request reviews.

### `format-review`

<!-- md:version 2.9.0 -->
<!-- md:default false -->
<!-- md:permission pull_request: write #pull-request-reviews -->

Set this option to `true` to enable Pull Request reviews from clang-format.

!!! info "Important"
    This feature requires special permissions to perform successfully.
    See our [documented permissions](permissions.md).

    See also [the PR review feature caveats](pr-review-caveats.md).

> [!NOTE]
> The [`no-lgtm`](#no-lgtm) option is applicable to Pull Request reviews.

## Outputs

This action creates 3 output variables. Even if the linting checks fail for source files this action will still pass, but users' CI workflows can use this action's outputs to exit the workflow early if that is desired.

### `checks-failed`

<!-- md:version 1.2.0 -->

The total number of concerns raised by both clang-format and clang-tidy.

### `clang-tidy-checks-failed`

<!-- md:version 2.7.2 -->

The total number of concerns raised by clang-tidy only.

### `clang-format-checks-failed`

<!-- md:version 2.7.2 -->

The total number of concerns raised by clang-format only.
