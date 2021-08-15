# C/C++ Lint Action

Github Actions for linting the C/C++ code. Integrated clang-tidy, clang-format checks.

## Integration with GitHub Actions

Just create a `yml` file under your GitHub repository. For example `.github/workflows/cpp-linter.yml`

```yml
name: cpp-linter

on: [pull_request]
jobs:
  cpp-linter:
    name: cpp-linter
    runs-on: ubuntu-latest
    steps:
      - name: C/C++ Lint Action
        uses: shenxianpeng/cpp-linter-action@master
        with:
          fetch-depth: 0
    env:
        GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

## Results of GitHub Actions

Here is a test repository [cpp-linter-action-demo](https://github.com/shenxianpeng/cpp-linter-action-demo) which has added `cpp-linter.yml`. when an unformatted c/c++ source file was committed and create a Pull Request will automatically recognize and add warning comments.

For example, this PR [#7](https://github.com/shenxianpeng/cpp-linter-action-demo/pull/7), and warning message like below:

![github-actions bot](https://github.com/shenxianpeng/cpp-linter-action-demo/blob/master/img/result.png?raw=true)

Please feel free to commit code to the [demo](https://github.com/shenxianpeng/cpp-linter-action-demo) repo and create a Pull Request to see how the process works.

If you have any suggestions or contributions, welcome to PR [here](https://github.com/shenxianpeng/cpp-linter-action).
