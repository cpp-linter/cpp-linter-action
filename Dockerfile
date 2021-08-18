FROM ubuntu:latest

LABEL com.github.actions.name="cpp-linter check"
LABEL com.github.actions.description="Lint your code with clang-tidy in parallel to your builds"
LABEL com.github.actions.icon="code"
LABEL com.github.actions.color="gray-dark"

LABEL repository="https://github.com/shenxianpeng/cpp-linter-action"
LABEL maintainer="shenxianpeng <20297606+shenxianpeng@users.noreply.github.com>"

# WORKDIR /build
RUN apt-get update
RUN apt-get -qq -y install curl clang-tidy cmake jq clang clang-format

COPY runchecks.sh /entrypoint.sh
RUN chmod +x /entrypoint.ch
CMD ["bash", "/entrypoint.sh", "$@"]
