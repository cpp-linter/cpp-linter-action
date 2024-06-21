---
name: Report a problem
about: Create a report to let us help you
title: ''
labels: []
assignees: ''

body:
  - type: textarea
    attributes:
      label: What events trigger your workflow?
      description: >-
        Please copy and paste the workflow triggers.
        If you are using a resuable workflow (`workflow_dispatch` event),
        then please also include the workflow triggers that the calling workflow uses.
      placeholder: |-
        on:
        pull_request:
          branches: [main, master, develop]
          paths: ['**.c', '**.cpp', '**.h', '**.hpp', '**.cxx', '**.hxx', '**.cc', '**.hh', '**CMakeLists.txt', 'meson.build', '**.cmake']
        push:
          branches: [main, master, develop]
          paths: ['**.c', '**.cpp', '**.h', '**.hpp', '**.cxx', '**.hxx', '**.cc', '**.hh', '**CMakeLists.txt', 'meson.build', '**.cmake']
      render: yml

  - type: textarea
    attributes:
      label: What OS does your workflow use?
      description: >-
        Please tell us what OS the workflow [`runs-on`](https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions#jobsjob_idruns-on).
        If you are using an additional [`container`](https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions#jobsjob_idcontainer),
        then please also include that information here.
      placeholder: |-
        runs-on: ubuntu-latest
        container: node:18
      render: yml

  - type: textarea
    attributes:
      label: How is cpp-linter-action configured?
      description: >-
        Please copy and paste the version and inputs used to run cpp-linter-action.
      placeholder: |-
        - uses: cpp-linter/cpp-linter-action@v2
          id: linter
          env:
            GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          with:
            style: 'file'
            tidy-checks: ''
      render: yml

  - type: textarea
    attributes:
      label: What was the unexpected behavior?
      description: |-
        Use this area to describe what behavior you expected and what behavior you observed.
        Please be clear and concise as possible. Use screenshots if that would help. Most users
        use this to paste the workflow logs.
      placeholder: You can use markdown syntax here
