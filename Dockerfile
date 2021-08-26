FROM xianpengshen/clang-tools:all

# WORKDIR option is set by the github action to the environment variable GITHUB_WORKSPACE.
# See https://docs.github.com/en/actions/creating-actions/dockerfile-support-for-github-actions#workdir


LABEL com.github.actions.name="cpp-linter check"
LABEL com.github.actions.description="Lint your code with clang-tidy in parallel to your builds"
LABEL com.github.actions.icon="code"
LABEL com.github.actions.color="gray-dark"

LABEL repository="https://github.com/shenxianpeng/cpp-linter-action"
LABEL maintainer="shenxianpeng <20297606+shenxianpeng@users.noreply.github.com>"

RUN apt-get update
RUN apt-get -y install python3-pip
# curl jq

# COPY runchecks.sh /entrypoint.sh
# RUN chmod +x /entrypoint.sh
COPY python_action/ /python_action/
COPY setup.py /setup.py
RUN python3 /setup.py install

# github action args use the CMD option
# See https://docs.github.com/en/actions/creating-actions/metadata-syntax-for-github-actions#runsargs
# also https://docs.docker.com/engine/reference/builder/#cmd
# ENTRYPOINT [ "/entrypoint.sh" ]
ENTRYPOINT [ "python3", "-m", "python_action.run" ]
