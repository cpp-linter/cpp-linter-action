FROM node:11-stretch

LABEL com.github.actions.name="clang-tidy check"
LABEL com.github.actions.description="Lint your code with clang-tidy in parallel to your builds"
LABEL com.github.actions.icon="code"
LABEL com.github.actions.color="gray-dark"

LABEL repository="https://github.com/muxee/clang-tidy-action"
LABEL maintainer="rufi <rufi+oss@muxee.org>"

WORKDIR /app

COPY package*.json ./
RUN npm ci --only=production

COPY . .

ENTRYPOINT ["node", "/app/index.js"]
