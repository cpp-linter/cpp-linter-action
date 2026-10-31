#!/usr/bin/env bash
# The script behind format/action.yml: download clang-format, work out which files
# and lines changed, check them, report annotations and a step summary, and exit 1
# when anything is not formatted. Inputs come from the INPUT_* variables set in
# action.yml; the GITHUB_* and RUNNER_* variables come from the runner.
set -euo pipefail

INDEX_URL="${CLANG_TOOLS_INDEX_URL:-https://cpp-linter.github.io/clang-tools-static-binaries/index.json}"
version="${INPUT_VERSION:-21}"
style="${INPUT_STYLE:-file}"
extensions="${INPUT_EXTENSIONS:-c,h,C,H,cpp,hpp,cc,hh,c++,h++,cxx,hxx}"
files_changed_only="${INPUT_FILES_CHANGED_ONLY:-true}"
lines_changed_only="${INPUT_LINES_CHANGED_ONLY:-true}"
summary_file="${GITHUB_STEP_SUMMARY:-/dev/null}"
output_file="${GITHUB_OUTPUT:-/dev/null}"

fail() {
  echo "::error title=cpp-linter format::$*"
  exit 1
}

is_true() {
  case "$1" in true | True | TRUE | 1) return 0 ;; *) return 1 ;; esac
}

# Escape a value for a workflow command property such as file=.
escape_property() {
  local value="${1//%/%25}"
  value="${value//$'\r'/%0D}"
  value="${value//$'\n'/%0A}"
  value="${value//:/%3A}"
  printf '%s' "${value//,/%2C}"
}

# Read from stdin: with a Windows path (backslashes) sha512sum puts a "\" before the hash.
sha512() {
  if command -v sha512sum >/dev/null; then
    sha512sum <"$1" | cut -d' ' -f1
  else
    shasum -a 512 <"$1" | cut -d' ' -f1
  fi
}

# --- 1. Get clang-format -----------------------------------------------------

case "${RUNNER_OS:-$(uname -s)}" in
  Linux) os=linux ;;
  macOS | Darwin) os=macos ;;
  Windows | MINGW* | MSYS* | CYGWIN*) os=windows ;;
  *) fail "unsupported runner OS: ${RUNNER_OS:-$(uname -s)}" ;;
esac
case "${RUNNER_ARCH:-$(uname -m)}" in
  X64 | x86_64 | AMD64) arch=amd64 ;;
  ARM64 | arm64 | aarch64) arch=arm64 ;;
  *) fail "unsupported runner architecture: ${RUNNER_ARCH:-$(uname -m)}" ;;
esac
command -v jq >/dev/null || fail "jq is required (it is preinstalled on GitHub-hosted runners)"

work_dir="${RUNNER_TEMP:-/tmp}/cpp-linter-format"
mkdir -p "$work_dir"
curl -fsSL --retry 3 -o "$work_dir/index.json" "$INDEX_URL" \
  || fail "could not download $INDEX_URL"

asset="$(jq -c --arg v "$version" --arg p "$os-$arch" \
  '.versions[$v].tools["clang-format"][$p] // empty' "$work_dir/index.json")"
[ -n "$asset" ] || fail "clang-format $version is not available for $os-$arch; use a major version from $(jq -r '.versions | keys | join(", ")' "$work_dir/index.json")"
full_version="$(jq -r --arg v "$version" '.versions[$v].version' "$work_dir/index.json")"
bin="$work_dir/$(jq -r .name <<<"$asset")"
expected_sha="$(jq -r .sha512 <<<"$asset")"

if [ ! -f "$bin" ] || [ "$(sha512 "$bin")" != "$expected_sha" ]; then
  curl -fsSL --retry 3 -o "$bin" "$(jq -r .url <<<"$asset")" \
    || fail "could not download clang-format $full_version"
  [ "$(sha512 "$bin")" = "$expected_sha" ] || fail "SHA-512 mismatch for $(basename "$bin")"
  chmod +x "$bin"
fi
echo "Using $("$bin" --version)"
echo "clang-format-version=$full_version" >>"$output_file"

# --- 2. Work out what to check -----------------------------------------------

cd "$(git rev-parse --show-toplevel)"

pathspecs=()
IFS=',' read -r -a exts <<<"$extensions"
for ext in "${exts[@]}"; do
  ext="${ext//[[:space:]]/}"
  [ -n "$ext" ] && pathspecs+=("*.${ext#.}")
done
[ "${#pathspecs[@]}" -gt 0 ] || fail "the extensions input is empty"
while IFS= read -r pattern; do
  pattern="$(sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//' <<<"$pattern")"
  [ -n "$pattern" ] && pathspecs+=(":(exclude)$pattern")
done < <(tr '|' '\n' <<<"${INPUT_IGNORE:-}")

parents_of_head() {
  git cat-file -p HEAD | sed -n 's/^parent //p'
}

base=""
if is_true "$files_changed_only"; then
  event_file="${GITHUB_EVENT_PATH:-/dev/null}"
  case "${GITHUB_EVENT_NAME:-}" in
    pull_request | pull_request_target)
      # actions/checkout checks out the merge commit: its first parent is the base
      # branch, its second the pull request head.
      head_sha="$(jq -r '.pull_request.head.sha // empty' "$event_file")"
      read -r -a parents <<<"$(parents_of_head | tr '\n' ' ')"
      if [ "${#parents[@]}" -eq 2 ] && [ "${parents[1]}" = "$head_sha" ]; then
        base="${parents[0]}"
      elif [ "$GITHUB_EVENT_NAME" = pull_request_target ] && [ "$(git rev-parse HEAD)" != "$head_sha" ]; then
        # The default pull_request_target checkout is the base branch: nothing to check.
        fail "on pull_request_target the checkout is the base branch, not the pull request; use the pull_request event, or check out refs/pull/<number>/merge"
      else
        base="$(jq -r '.pull_request.base.sha // empty' "$event_file")"
      fi
      ;;
    merge_group)
      base="$(jq -r '.merge_group.base_sha // empty' "$event_file")"
      ;;
    push)
      base="$(jq -r '.before // empty' "$event_file")"
      if [ -z "$base" ] || [ "$base" = "0000000000000000000000000000000000000000" ]; then
        base="$(parents_of_head | head -n 1)"  # a new branch: check its last commit
      fi
      ;;
  esac
  [ -n "$base" ] || echo "No base commit for the '${GITHUB_EVENT_NAME:-}' event: checking every file."
fi

if [ -n "$base" ] && ! git cat-file -e "$base^{commit}" 2>/dev/null; then
  echo "Fetching base commit $base"
  if ! git fetch --quiet --no-tags --no-recurse-submodules --depth=1 origin "$base" 2>/dev/null; then
    auth="$(printf 'x-access-token:%s' "${INPUT_TOKEN:-}" | base64 | tr -d '\n')"
    git -c http.extraHeader="AUTHORIZATION: basic $auth" \
      fetch --quiet --no-tags --no-recurse-submodules --depth=1 origin "$base" \
      || fail "could not fetch the base commit $base; set files-changed-only: false to check every file"
  fi
fi

# One line per file: "<path>\t<start:end> <start:end> ..." (no ranges = whole file).
targets="$work_dir/targets.tsv"
if [ -z "$base" ]; then
  git ls-files -z -- "${pathspecs[@]}" | tr '\0' '\n' >"$targets"
  scope="every file"
elif ! is_true "$lines_changed_only"; then
  git diff -z --name-only --diff-filter=d "$base" -- "${pathspecs[@]}" | tr '\0' '\n' >"$targets"
  scope="changed files"
else
  git -c core.quotePath=false diff -U0 --no-color --no-ext-diff --diff-filter=d \
    --src-prefix=a/ --dst-prefix=b/ "$base" -- "${pathspecs[@]}" \
    | awk '
        /^diff --git / { header = 1; file = ""; next }
        header && /^\+\+\+ / { file = substr($0, 7); next }
        /^@@ / {
          header = 0
          if (file == "") next
          split($3, range, ",")
          start = substr(range[1], 2) + 0
          count = (range[2] == "") ? 1 : range[2] + 0
          if (count == 0) next
          if (!(file in lines)) order[++n] = file
          lines[file] = lines[file] (lines[file] == "" ? "" : " ") start ":" (start + count - 1)
        }
        END { for (i = 1; i <= n; i++) print order[i] "\t" lines[order[i]] }
      ' >"$targets"
  scope="changed lines"
fi

# --- 3. Check ------------------------------------------------------------------

checked=0
failed=0
failed_files=()
diffs="$work_dir/diffs.patch"
: >"$diffs"

while IFS=$'\t' read -r file ranges; do
  # Skip symlinks: a tracked link could point clang-format at a file outside the checkout.
  [ -n "$file" ] && [ -f "$file" ] && [ ! -L "$file" ] || continue
  checked=$((checked + 1))
  args=("--style=$style")
  for range in $ranges; do
    args+=("--lines=$range")
  done

  if output="$("$bin" "${args[@]}" --dry-run --Werror -- "$file" 2>&1)"; then
    continue
  fi
  failed=$((failed + 1))
  failed_files+=("$file")

  violations="$(grep -F -e '[-Wclang-format-violations]' <<<"$output" || true)"
  if [ -z "$violations" ]; then
    # Not a style issue: a bad .clang-format, an unreadable file, ...
    echo "::error file=$(escape_property "$file"),title=clang-format failed::$(head -n 1 <<<"$output")"
    echo "$output"
    continue
  fi
  # One annotation per line, however many places on it clang-format would change.
  last_line=""
  while IFS= read -r line; do
    if [[ "$line" =~ :([0-9]+):([0-9]+):\ error:\ (.*)$ ]] && [ "${BASH_REMATCH[1]}" != "$last_line" ]; then
      last_line="${BASH_REMATCH[1]}"
      message="${BASH_REMATCH[3]% \[-Wclang-format-violations\]}"
      echo "::error file=$(escape_property "$file"),line=$last_line,col=${BASH_REMATCH[2]},title=clang-format::$message"
    fi
  done <<<"$violations"

  formatted="$work_dir/formatted"
  "$bin" "${args[@]}" -- "$file" >"$formatted" 2>/dev/null || true
  {
    diff -u --label "a/$file" --label "b/$file" "$file" "$formatted" || true
  } >>"$diffs"
done <"$targets"

echo "checks-failed=$failed" >>"$output_file"

# --- 4. Report -----------------------------------------------------------------

if [ "$failed" -gt 0 ]; then
  echo "::group::Changes clang-format would make"
  cat "$diffs"
  echo "::endgroup::"
fi

{
  if [ "$failed" -eq 0 ]; then
    echo "### clang-format: all $checked checked file(s) are formatted"
  else
    echo "### clang-format: $failed of $checked checked file(s) need formatting"
  fi
  echo
  echo "clang-format $full_version, \`--style=$style\`, checked $scope."
  if [ "$failed" -gt 0 ]; then
    echo
    for file in "${failed_files[@]}"; do
      echo "- \`$file\`"
    done
    echo
    echo "<details><summary>Changes clang-format would make</summary>"
    echo
    echo '```diff'
    head -n 2000 "$diffs"
    [ "$(wc -l <"$diffs")" -le 2000 ] || echo "... (cut; the full diff is in the job log)"
    echo '```'
    echo
    echo "</details>"
    echo
    if [ -n "$base" ] && is_true "$lines_changed_only"; then
      echo "To fix only the changed lines locally, run \`git clang-format <base branch>\`."
    else
      echo "To fix them locally, run \`clang-format -i\` on the files above."
    fi
  fi
} >>"$summary_file"

if [ "$failed" -gt 0 ]; then
  echo "$failed of $checked file(s) need formatting."
  exit 1
fi
echo "All $checked checked file(s) are formatted."
