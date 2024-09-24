[file-annotations]: https://cpp-linter.github.io/cpp-linter-action/inputs-outputs/#file-annotations
[thread-comments]: https://cpp-linter.github.io/cpp-linter-action/inputs-outputs/#thread-comments
[step-summary]: https://cpp-linter.github.io/cpp-linter-action/inputs-outputs/#step-summary
[tidy-review]: https://cpp-linter.github.io/cpp-linter-action/inputs-outputs/#tidy-review
[format-review]: https://cpp-linter.github.io/cpp-linter-action/inputs-outputs/#format-review

[io-doc]: https://cpp-linter.github.io/cpp-linter-action/inputs-outputs
[recipes-doc]: https://cpp-linter.github.io/cpp-linter-action/examples

[format-annotations-preview]: https://raw.githubusercontent.com/cpp-linter/cpp-linter-action/main/docs/images/annotations-clang-format.png
[tidy-annotations-preview]: https://raw.githubusercontent.com/cpp-linter/cpp-linter-action/main/docs/images/annotations-clang-tidy.png
[thread-comment-preview]: https://raw.githubusercontent.com/cpp-linter/cpp-linter-action/main/docs/images/comment.png
[step-summary-preview]: https://raw.githubusercontent.com/cpp-linter/cpp-linter-action/main/docs/images/step-summary.png
[tidy-review-preview]: https://raw.githubusercontent.com/cpp-linter/cpp-linter-action/main/docs/images/tidy-review.png
[format-review-preview]: https://raw.githubusercontent.com/cpp-linter/cpp-linter-action/main/docs/images/format-review.png
[format-suggestion-preview]: https://raw.githubusercontent.com/cpp-linter/cpp-linter-action/main/docs/images/format-suggestion.png

<!--README-start-->

# C/C++ Linter Action <sub><sup>| clang-format & clang-tidy</sup></sub>

![GitHub release (latest SemVer)](https://img.shields.io/github/v/release/cpp-linter/cpp-linter-action)
[![Used by](https://img.shields.io/static/v1?label=Used%20by&message=652&color=informational&logo=slickpic)](https://github.com/cpp-linter/cpp-linter-action/network/dependents)<!-- used by badge -->
[![GitHub marketplace](https://img.shields.io/badge/marketplace-C%2FC%2B%2B%20Linter-blue?logo=github)](https://github.com/marketplace/actions/c-c-linter)
[![cpp-linter](https://github.com/cpp-linter/cpp-linter-action/actions/workflows/cpp-linter.yml/badge.svg)](https://github.com/cpp-linter/cpp-linter-action/actions/workflows/cpp-linter.yml)
[![MkDocs Deploy](https://github.com/cpp-linter/cpp-linter-action/actions/workflows/mkdocs-deploy.yml/badge.svg)](https://github.com/cpp-linter/cpp-linter-action/actions/workflows/mkdocs-deploy.yml)
![GitHub](https://img.shields.io/github/license/cpp-linter/cpp-linter-action?label=license&logo=github)

A Github Action for linting C/C++ code integrating clang-tidy and clang-format
to collect feedback provided in the form of
[`file-annotations`][file-annotations], [`thread-comments`][thread-comments],
workflow [`step-summary`][step-summary], and Pull Request reviews (with
[`tidy-review`][tidy-review] or [`format-review`][format-review]).

> [!WARNING]
> We only support Linux runners using a Debian based Linux OS (like Ubuntu and many others).
>
> MacOS and Windows runners are supported as well.

## What's New

v2

* Change action from using docker to composite steps
  * improve workflow runs times from 1m 24s (using v1) to 6-20s (for simple workflow runs).
  * better support for the database input option (which was broken with the docker environment in v1).
  * better support cross-compilation
  * better support 3rd party libraries
* Includes many issues and enhancements. See [#87](https://github.com/cpp-linter/cpp-linter-action/issues/87) for details.

Refer [here](https://github.com/cpp-linter/cpp-linter-action/tree/v1) for previous versions.

## Usage

> [!NOTE]
> Python 3.10 needs to be installed in the docker image if your workflow is
> [running jobs in a container](https://docs.github.com/en/actions/using-jobs/running-jobs-in-a-container)
> (see discussion in [#185](https://github.com/cpp-linter/cpp-linter-action/issues/185)).
> Our intention is to synchronize with the default python version included with Ubuntu latest LTS releases.

Create a new GitHub Actions workflow in your project, e.g. at [.github/workflows/cpp-linter.yml](https://github.com/cpp-linter/cpp-linter-action/blob/main/.github/workflows/cpp-linter.yml)

The content of the file should be in the following format.

```yaml
    steps:
      - uses: actions/checkout@v4
      - uses: cpp-linter/cpp-linter-action@v2
        id: linter
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        with:
          style: 'file'  # Use .clang-format config file
          tidy-checks: '' # Use .clang-tidy config file
          # only 'update' a single comment in a pull request's thread.
          thread-comments: ${{ github.event_name == 'pull_request' && 'update' }}
      - name: Fail fast?!
        if: steps.linter.outputs.checks-failed > 0
        run: exit 1
```

For all explanations of our available input parameters and output variables, see our
[Inputs and Outputs document][io-doc].

See also our [example recipes][recipes-doc].

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


## Add C/C++ Linter Action badge in README

You can show C/C++ Linter Action status with a badge in your repository README

Example

```markdown
[![cpp-linter](https://github.com/cpp-linter/cpp-linter-action/actions/workflows/cpp-linter.yml/badge.svg)](https://github.com/cpp-linter/cpp-linter-action/actions/workflows/cpp-linter.yml)
```

[![cpp-linter](https://github.com/cpp-linter/cpp-linter-action/actions/workflows/cpp-linter.yml/badge.svg)](https://github.com/cpp-linter/cpp-linter-action/actions/workflows/cpp-linter.yml)

## Have question or feedback?

To provide feedback (requesting a feature or reporting a bug) please post to [issues](https://github.com/cpp-linter/cpp-linter-action/issues).

## License

The scripts and documentation in this project are released under the [MIT License](https://github.com/cpp-linter/cpp-linter-action/blob/main/LICENSE)

<!--README-end-->
