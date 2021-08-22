# C/C++ Lint Action

Github Actions for linting the C/C++ code. Integrated clang-tidy, clang-format checks.

## Integration with GitHub Actions

Just create a `yml` file under your GitHub repository. For example `.github/workflows/cpp-linter.yml`

!!! Requires `secrets.GITHUB_TOKEN` set to an environment variable named `GITHUB_TOKEN`.

```yml
name: cpp-linter

# Triggers the workflow on push or pull request events
on:
  push:
  pull_request:
    types: [opened]
jobs:
  cpp-linter:
    name: cpp-linter
    runs-on: ubuntu-latest
    steps:
      - name: C/C++ Lint Action
        env:
            GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        uses: shenxianpeng/cpp-linter-action@master
        with:
          style: 'file'
```
## Optional Inputs

| Input name | default value | Description |
|------------|---------------|-------------|
| style | 'llvm' | The style rules to use. Set this to 'file' to have clang-format use the closest relative .clang-format file. |
| extensions | 'c,h,C,H,cpp,hpp,cc,hh,c++,h++,cxx,hxx' | The file extensions to run the action against. This is a comma-separated string. |
| tidy-checks | 'boost-\*,bugprone-\*,performance-\*,<br>readability-\*,portability-\*,<br>modernize-\*,clang-analyzer-\*,<br>cppcoreguidelines-\*' | A string of regex-like patterns specifying what checks clang-tidy will use.|
| repo-root | '.' | The relative path to the repository root directory. This path is relative to path designated by the runner's GITHUB_WORKSPACE environment variable. |
| version | '10' | The desired version of the clang tools to use. Accepted options are strings which can be 6.0, 7, 8, 9, 10, 11, 12. |

### Outputs

This action creates 1 output variable named `checks-failed`. Even if the linting checks fail for source files this action will still pass, but users' CI workflows can use this action's output to exit the workflow early if that is desired.

## Results of GitHub Actions

![github-actions bot](./demo/result.png)

Behind the scenes, this is because this repository has added `test.yml` under `.github/workflows/`. When an unformatted C/C++ source file was committed and create a Pull Request will automatically recognize and add warning comments.

Please feel free to commit code to the `test` branch of this repository or create a Pull Request to see how the process works.

For example, this test PR [#6](https://github.com/shenxianpeng/cpp-linter-action/pull/5) and github-actions bot comments [link](https://github.com/shenxianpeng/cpp-linter-action/pull/5#commitcomment-55252014).

## Contribution

If you have any suggestions or contributions, welcome to PR [here](https://github.com/shenxianpeng/cpp-linter-action).
