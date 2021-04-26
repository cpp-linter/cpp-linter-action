# cpp-linter-action

Github Actions for linting the C/C++ code. Uses clang-tidy, clang-format, and cppcheck.

## Integration with GitHub Actions

For example, create a `.yml` file like `.github/workflows/cpp-linter.yml`.

```
name: cpp-linter

on: [pull_request]
jobs:
  cpp-linter:
    name: cpp-linter
    runs-on: ubuntu-latest
    steps:
      - name: cpp-linter
        uses: shenxianpeng/cpp-linter-action@master
    env:
        GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```
## Results of GitHub Actions

This one has a test repository: [cpp-linter-action-demo](https://github.com/shenxianpeng/cpp-linter-action-demo)

You can feel free to commit C/C++ code and then see the actual results via Pull Request. such as this PR [#3](https://github.com/shenxianpeng/cpp-linter-action-demo/pull/3)

![github-actions bot](https://github.com/shenxianpeng/cpp-linter-action-demo/blob/master/img/result.png?raw=true)

