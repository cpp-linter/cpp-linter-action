FROM ubuntu:latest

LABEL com.github.actions.name="c-linter check"
LABEL com.github.actions.description="Lint your code with clang-tidy in parallel to your builds"
LABEL com.github.actions.icon="code"
LABEL com.github.actions.color="gray-dark"

LABEL repository="https://github.com/ArtificialAmateur/cpp-linter-action"
LABEL maintainer="ArtificialAmateur <20297606+ArtificialAmateur@users.noreply.github.com>"

WORKDIR /build
RUN apt-get update
RUN apt-get -qq -y install curl clang-tidy cmake jq clang cppcheck clang-format

ADD runchecks.sh /entrypoint.sh
COPY . .
CMD ["bash", "/entrypoint.sh"]
