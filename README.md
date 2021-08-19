# C/C++ Lint Action

Github Actions for linting the C/C++ code. Integrated clang-tidy, clang-format checks.

## Integration with GitHub Actions

Just create a `yml` file under your GitHub repository. For example `.github/workflows/cpp-linter.yml`

!!! Requires `secrets.GITHUB_TOKEN` set to an environment variable name "GITHUB_TOKEN".

```yml
name: cpp-linter

# Triggers the workflow on push or pull request events
on: [push, pull_request]
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

## Results of GitHub Actions

Here is a test repository [cpp-linter-action-demo](https://github.com/shenxianpeng/cpp-linter-action-demo) which has added `cpp-linter.yml`. when an unformatted C/C++ source file was committed and create a Pull Request will automatically recognize and add warning comments.

For example, this PR [#7](https://github.com/shenxianpeng/cpp-linter-action-demo/pull/7), and warning message like below:

![github-actions bot](https://github.com/shenxianpeng/cpp-linter-action-demo/blob/master/img/result.png?raw=true)

Please feel free to commit code to the [demo](https://github.com/shenxianpeng/cpp-linter-action-demo) repository and create a Pull Request to see how the process works.

If you have any suggestions or contributions, welcome to PR [here](https://github.com/shenxianpeng/cpp-linter-action).
