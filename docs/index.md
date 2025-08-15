[file-annotations]: inputs-outputs.md#file-annotations
[thread-comments]: inputs-outputs.md#thread-comments
[step-summary]: inputs-outputs.md#step-summary
[tidy-review]: inputs-outputs.md#tidy-review
[format-review]: inputs-outputs.md#format-review

[io-doc]: inputs-outputs.md
[recipes-doc]: examples/index.md

{%
    include "../README.md"
    start="<!-- start -->"
    end="<!-- stop -->"
%}

## Example

### Annotations

Using [`--file-annotations`][file-annotations]:

#### clang-format annotations

![format-annotation-dark](images/format-annotation-dark.png){ .dark-only }
![format-annotation-light](images/format-annotation-light.png){ .light-only }

#### clang-tidy annotations

![tidy-annotation-dark](images/tidy-annotation-dark.png){ .dark-only }
![tidy-annotation-light](images/tidy-annotation-light.png){ .light-only }

### Thread Comment

Using [`--thread-comments`][thread-comments]:

![thread-comment-dark](images/thread-comment-dark.png){ .dark-only }
![thread-comment-light](images/thread-comment-light.png){ .light-only }

??? example "Expanded"

    ![thread-comment-expanded-dark](images/thread-comment-expanded-dark.png){ .dark-only }
    ![thread-comment-expanded-light](images/thread-comment-expanded-light.png){ .light-only }

### Step Summary

Using [`--step-summary`][step-summary]:

![step-summary-dark](images/step-summary-dark.png){ .dark-only }
![step-summary-light](images/step-summary-light.png){ .light-only }

### Pull Request Review

![review-summary-dark](images/review-summary-dark.png){ .dark-only }
![review-summary-light](images/review-summary-light.png){ .light-only }

#### clang-tidy suggestion

Using [`--tidy-review`][tidy-review]:

![tidy-review-dark](images/tidy-review-dark.png){ .dark-only }
![tidy-review-light](images/tidy-review-light.png){ .light-only }

#### clang-format suggestion

Using [`--format-review`][format-review]:

![format-review-dark](images/format-review-dark.png){ .dark-only }
![format-review-light](images/format-review-light.png){ .light-only }

{%
    include "../README.md"
    start="<!-- resume -->"
%}
