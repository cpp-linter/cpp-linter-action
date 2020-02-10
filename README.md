Github action for linting the C code.
Uses clang-tidy, clang-format, and cppcheck.

Example of usage:
```
name: c-linter

on: [pull_request]
jobs:
  c-linter:
    name: c-linter
    runs-on: ubuntu-latest
    steps:
      - name: c-linter
        uses: smay1613/clang-tidy-action@master
    env:
        GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```
