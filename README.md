<!-- markdownlint-disable MD041 -->

[file-annotations]: https://cpp-linter.github.io/cpp-linter-action/inputs-outputs/#file-annotations
[thread-comments]: https://cpp-linter.github.io/cpp-linter-action/inputs-outputs/#thread-comments
[step-summary]: https://cpp-linter.github.io/cpp-linter-action/inputs-outputs/#step-summary
[tidy-review]: https://cpp-linter.github.io/cpp-linter-action/inputs-outputs/#tidy-review
[format-review]: https://cpp-linter.github.io/cpp-linter-action/inputs-outputs/#format-review

[io-doc]: https://cpp-linter.github.io/cpp-linter-action/inputs-outputs
[recipes-doc]: https://cpp-linter.github.io/cpp-linter-action/examples
[permissions-doc]: https://cpp-linter.github.io/cpp-linter-action/permissions
[app-token-doc]: https://cpp-linter.github.io/cpp-linter-action/permissions/#github-app-token
[tools-doc]: https://cpp-linter.github.io/cpp-linter-action/required-tools

[format-annotations-preview]: https://raw.githubusercontent.com/cpp-linter/cpp-linter-action/main/docs/images/annotations-clang-format.png
[tidy-annotations-preview]: https://raw.githubusercontent.com/cpp-linter/cpp-linter-action/main/docs/images/annotations-clang-tidy.png
[thread-comment-preview]: https://raw.githubusercontent.com/cpp-linter/cpp-linter-action/main/docs/images/comment.png
[step-summary-preview]: https://raw.githubusercontent.com/cpp-linter/cpp-linter-action/main/docs/images/step-summary.png
[tidy-review-preview]: https://raw.githubusercontent.com/cpp-linter/cpp-linter-action/main/docs/images/tidy-review.png
[format-review-preview]: https://raw.githubusercontent.com/cpp-linter/cpp-linter-action/main/docs/images/format-review.png
[format-suggestion-preview]: https://raw.githubusercontent.com/cpp-linter/cpp-linter-action/main/docs/images/format-suggestion.png

<!--README-start-->

# cpp-linter-action

[![release](https://img.shields.io/github/v/release/cpp-linter/cpp-linter-action?label=release&labelColor=454a63&color=007ec6)](https://github.com/cpp-linter/cpp-linter-action/releases)
[![ci](https://img.shields.io/github/actions/workflow/status/cpp-linter/cpp-linter-action/self-test.yml?branch=main&label=ci&labelColor=454a63)](https://github.com/cpp-linter/cpp-linter-action/actions/workflows/self-test.yml)
[![part of cpp-linter](https://img.shields.io/badge/part%20of-cpp--linter-ffc20a?labelColor=454a63)](https://cpp-linter.github.io/)

A GitHub Action that checks the C and C++ files a pull request changes with clang-format and
clang-tidy, and reports the findings as [`file-annotations`][file-annotations],
[`thread-comments`][thread-comments], a workflow [`step-summary`][step-summary] and pull request
reviews (with [`tidy-review`][tidy-review] or [`format-review`][format-review]).

[Website](https://cpp-linter.github.io/) ·
[Documentation](https://cpp-linter.github.io/cpp-linter-action/) ·
[Marketplace](https://github.com/marketplace/actions/c-c-linter) ·
[Get started](https://cpp-linter.github.io/getting-started/#on-every-pull-request) ·
[Discussions](https://github.com/orgs/cpp-linter/discussions)

## Quick start

Save this as `.github/workflows/cpp-linter.yml`:

```yaml
name: cpp-linter
on: pull_request

jobs:
  cpp-linter:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      pull-requests: write
    steps:
      - uses: actions/checkout@v7
      - uses: cpp-linter/cpp-linter-action@v2
        id: linter
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        with:
          version: '21'
          style: file
          tidy-checks: ''
          format-review: true
      - name: Fail on lint errors
        if: steps.linter.outputs.checks-failed > 0
        run: exit 1
```

- `style: file` and `tidy-checks: ''` use your `.clang-format` and `.clang-tidy`. `version` takes
  an LLVM major from 12 to 23; `21` is the default.
- Annotations in the diff view are on by default. `format-review`, `tidy-review` and
  `thread-comments` are opt-in and need `pull-requests: write`; turn on one of the two reviews, not
  both. `auto-fix` commits the clang-format fixes to the branch and needs `contents: write`.
- The action does not fail the job by itself; the last step does, using the `checks-failed`
  output.
- Pull requests from forks get a read-only token: annotations still appear, but reviews are not
  posted, and `thread-comments` would fail the step. Draft pull requests get no review.

## Usage

For all explanations of our available input parameters and output variables, see our
[Inputs and Outputs document][io-doc].

See also our [example recipes][recipes-doc].

### Post a thread comment

Set `thread-comments` to post the findings as a comment in the pull request thread. With
`update`, the action updates its existing comment instead of posting a new one:

```yaml
      - uses: cpp-linter/cpp-linter-action@v2
        id: linter
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        with:
          style: 'file'  # Use .clang-format config file
          tidy-checks: '' # Use .clang-tidy config file
          # only 'update' a single comment in a pull request thread.
          # Pull requests from forks get a read-only token, so skip the comment there.
          thread-comments: ${{ github.event.pull_request.head.repo.full_name == github.repository && 'update' }}
```

### Auto-fix clang-format issues

Set `auto-fix: 'true'` and the action applies `clang-format -i` to the files with style
issues and commits the result to the branch:

```yaml
    steps:
      - uses: actions/checkout@v7
      - uses: cpp-linter/cpp-linter-action@v2
        id: linter
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        with:
          style: 'file'
          auto-fix: 'true'  # automatically fix format issues
```

On `pull_request` events `actions/checkout` checks out the merge commit, so the action switches
the workspace to the pull request's head commit before it lints and commits.

> [!TIP]
> Commits pushed with the default `GITHUB_TOKEN` do not start new workflow runs,
> so CI does not re-check the auto-fix commit. To change that, check out and run
> the action with a [GitHub App token][app-token-doc].
>
> Do not add `[skip ci]` or any other [skip instruction][skip-doc] to
> `auto-fix-commit-msg`. The auto-fix commit becomes the head of the pull request,
> so its required checks skipped for `push` or `pull_request` events would stay
> pending and may cause a gap in quality control. A squash merge can also carry
> the instruction into your default branch.
>
> See [our documented permissions][permissions-doc] for the required scopes.

### Use your own GitHub App

Every feature above can run with a token minted from a GitHub App that you own
instead of the default `GITHUB_TOKEN`. Comments and reviews are then posted
under your App's name rather than `github-actions[bot]`, and commits pushed by
`auto-fix` do start new workflow runs. The token is minted inside the job, so
there is no server or webhook handling to host.

See [GitHub App token][app-token-doc] for the setup steps.

## Example

### Annotations

Using [`file-annotations`][file-annotations]:

#### clang-format annotations

![clang-format annotations][format-annotations-preview]

#### clang-tidy annotations

![clang-tidy annotations][tidy-annotations-preview]

### Thread Comment

Using [`thread-comments`][thread-comments]:

![sample thread-comment][thread-comment-preview]

### Step Summary

Using [`step-summary`][step-summary]:

![step summary][step-summary-preview]

### Pull Request Review

#### Only clang-tidy

Using [`tidy-review`][tidy-review]:

![sample tidy-review][tidy-review-preview]

#### Only clang-format

Using [`format-review`][format-review]:

![sample format-review][format-review-preview]

![sample format-suggestion][format-suggestion-preview]

## Supported runners

Linux, macOS and Windows runners are supported. On Linux, we only support a Debian-based Linux OS
(like Ubuntu and many others), because we first try to use the `apt` package manager to install
clang tools. Linux workflows that use a specific [`container`][gh-container-syntax] need a few
packages installed first. [Required tools][tools-doc] lists them and the sources each runner
installs the clang tools from.

## Used by

Projects from these organizations run cpp-linter-action on their default branch:

[<img src="https://avatars.githubusercontent.com/u/47359?s=40&v=4" width="20" height="20" alt=""> Apache](https://github.com/apache) ·
[<img src="https://avatars.githubusercontent.com/u/6210390?s=40&v=4" width="20" height="20" alt=""> Samsung](https://github.com/samsung) ·
[<img src="https://avatars.githubusercontent.com/u/1416818?s=40&v=4" width="20" height="20" alt=""> Bloomberg](https://github.com/bloomberg) ·
[<img src="https://avatars.githubusercontent.com/u/55295994?s=40&v=4" width="20" height="20" alt=""> Qualcomm](https://github.com/qualcomm) ·
[<img src="https://avatars.githubusercontent.com/u/19211038?s=40&v=4" width="20" height="20" alt=""> Nextcloud](https://github.com/nextcloud) ·
[<img src="https://avatars.githubusercontent.com/u/85452089?s=40&v=4" width="20" height="20" alt=""> CachyOS](https://github.com/CachyOS) ·
[<img src="https://avatars.githubusercontent.com/u/58793052?s=40&v=4" width="20" height="20" alt=""> Jupyter Xeus](https://github.com/jupyter-xeus) ·
[<img src="https://avatars.githubusercontent.com/u/60992508?s=40&v=4" width="20" height="20" alt=""> NNStreamer](https://github.com/nnstreamer) ·
[<img src="https://avatars.githubusercontent.com/u/34372050?s=40&v=4" width="20" height="20" alt=""> Zondax](https://github.com/Zondax) ·
[<img src="https://avatars.githubusercontent.com/u/3374594?s=40&v=4" width="20" height="20" alt=""> AppNeta](https://github.com/AppNeta) ·
[<img src="https://avatars.githubusercontent.com/u/6140118?s=40&v=4" width="20" height="20" alt=""> Chocolate Doom](https://github.com/chocolate-doom)

The [showcase](https://cpp-linter.github.io/showcase/) lists more projects that use it.

## Contributing

Read [CONTRIBUTING.md](https://github.com/cpp-linter/cpp-linter-action/blob/main/CONTRIBUTING.md) before you open a pull request, and report bugs or request features in [issues](https://github.com/cpp-linter/cpp-linter-action/issues).

## License

The scripts and documentation in this project are released under the [MIT License](https://github.com/cpp-linter/cpp-linter-action/blob/main/LICENSE)

[gh-container-syntax]: https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#jobsjob_idcontainer
[skip-doc]: https://docs.github.com/en/actions/how-tos/manage-workflow-runs/skip-workflow-runs

<!--README-end-->
