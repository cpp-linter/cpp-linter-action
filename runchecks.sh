#!/bin/bash

# global varibales
EXIT_CODE="0"
PAYLOAD_TIDY=""
FENCES=$'\n```\n'
OUTPUT=""
URLS=""
PATHNAMES=""
declare -a JSON_INDEX
FILES_LINK=""

# alias CLI args
args=("$@")
FMT_STYLE=${args[0]}
IFS=',' read -r -a FILE_EXT_LIST <<< "${args[1]}"
TIDY_CHECKS="${args[2]}"
cd "${args[3]}" || exit "1"
CLANG_VERSION="${args[4]}"


###################################################
# Set the exit code (for expected exit calls).
# Optional parameter overides action-specific logic
###################################################
set_exit_code () {
   if [[ $# -gt 0 ]]
   then
      EXIT_CODE="$1"
   else
      if [[ "$PAYLOAD_FORMAT" != "" || "$PAYLOAD_TIDY" != "" ]]
      then
         EXIT_CODE="1"
      fi
   fi
   echo "::set-output name=checks-failed::$EXIT_CODE"
}

###################################################
# Fetch JSON of event's changed files
###################################################
get_list_of_changed_files() {
   echo "GH_EVENT_PATH = $GITHUB_EVENT_PATH"
   echo "processing $GITHUB_EVENT_NAME event"
   # cat "$GITHUB_EVENT_PATH" | jq '.'

   # Use git REST API payload
   if [[ "$GITHUB_EVENT_NAME" == "push" ]]
   then
      FILES_LINK="$GITHUB_API_URL/repos/$GITHUB_REPOSITORY/commits/$GITHUB_SHA"
   elif [[ "$GITHUB_EVENT_NAME" == "pull_request" ]]
   then
      # FILES_LINK="$GITHUB_API_URL/repos/$GITHUB_REPOSITORY/pulls/<PR ID number>/files"
      # Get PR ID number from the event's JSON located in the runner's GITHUB_EVENT_PATH
      FILES_LINK="$(jq -r '.pull_request._links.self.href' "$GITHUB_EVENT_PATH")/files"
   fi

   # Download files list (another JSON containing files' names, URLS, statuses, & diffs/patches)
   echo "Fetching files list from $FILES_LINK"
   curl "$FILES_LINK" > .cpp_linter_action_changed_files.json
}

###################################################
# extract info from downloaded JSON file
###################################################
extract_changed_files_info() {
   # pull_request events have a slightly different JSON format than push events
   JSON_FILES=".["
   if [[ "$GITHUB_EVENT_NAME" == "push" ]]
   then
      JSON_FILES=".files["
   fi
   FILES_URLS_STRING=$(jq -r "$JSON_FILES].raw_url" .cpp_linter_action_changed_files.json)
   FILES_NAMES_STRING=$(jq -r "$JSON_FILES].filename" .cpp_linter_action_changed_files.json)

   # convert json info to arrays
   readarray -t URLS <<<"$FILES_URLS_STRING"
   readarray -t PATHNAMES <<<"$FILES_NAMES_STRING"

   # Initialize the `JSON_INDEX` array. This helps us keep track of the
   # source files' index in the JSON after calling `filter_out_source_files()` function.
   for index in "${!URLS[@]}"
   do
      # this will only be used when parsing diffs from the JSON
      JSON_INDEX[$index]=$index
   done
}

###################################################
# exclude undesired files (specified by the user)
###################################################
filter_out_non_source_files() {
   for index in "${!URLS[@]}"
   do
      is_supported=0
      for i in "${FILE_EXT_LIST[@]}"
      do
         if [[ ${URLS[index]} == *".$i" ]]
         then
            is_supported=1
            break
         fi
      done

      if [ $is_supported == 0 ]
      then
         unset -v "URLS[index]"
         unset -v "PATHNAMES[index]"
         unset -v "JSON_INDEX[index]"
      fi
   done

   # exit early if nothing to do
   if [ ${#URLS[@]} == 0 ]
   then
      set_exit_code "0"
      echo "No source files need checking!"
      exit $EXIT_CODE
   else
      echo "File names: ${PATHNAMES[*]}"
   fi
}

###################################################
# Download the files if not present.
# This function assumes that the working directory is the root of the invoking repo.
# Note that all github actions are run in path specified by the environment variable GITHUB_WORKSPACE.
###################################################
verify_files_are_present() {
   # URLS, PATHNAMES, & PATCHES are parallel arrays
   for index in "${!PATHNAMES[@]}"
   do
      if [[ ! -f "${PATHNAMES[index]}" ]]
      then
         echo "Downloading ${URLS[index]}"
         curl --location --insecure --remote-name "${URLS[index]}"
      fi
   done
}

###################################################
# get the patch info from the JSON.
# required parameter is the index in the JSON_INDEX array
###################################################
get_patch_info() {
   # patches are multiline strings. Thus, they need special attention because of the '\n' used within.
   #
   # a git diff (aka "patch" in the REST API) can have multiple "hunks" for a single file.
   # hunks start with `@@ -<start-line>,<number of lines> +<start-line>,<number of lines> @@`
   # A positive sign indicates the incoming changes, while a negative sign indicates existing code that was changed
   # Any changed lines will also have a prefixed `-` or `+`.

   file_status=$(jq -r "$JSON_FILES${JSON_INDEX[$1]}].status" .cpp_linter_action_changed_files.json)

   # we only need the first line stating the line numbers changed (ie "@@ -1,5 +1,5 @@"")
   patched_lines=$(jq -r -c "$JSON_FILES${JSON_INDEX[$1]}].patch" .cpp_linter_action_changed_files.json)
   patches=$(echo "$patched_lines" | grep -o "@@ \\-[1-9]*,[1-9]* +[1-9]*,[1-9]* @@" | grep -o " +[1-9]*,[1-9]*" | tr -d "\\n" | sed 's; +;;; s;+;;g')

   # if there is no patch field, we need to handle 'renamed' as an edgde case
   if [[ "$patches" == "" ]]
   then
      echo "${PATHNAMES[$1]} was $file_status"
      # don't bother checking renamed files with no changes to file's content
      patches="0,0"
   fi
   echo "$patches"
}

###################################################
# execute clang-tidy/format & assemble a unified OUTPUT
###################################################
capture_clang_tools_output() {
   clang-tidy --version

   for index in "${!URLS[@]}"
   do
      filename=$(basename ${URLS[index]})
      if [[ -f "${PATHNAMES[index]}" ]]
      then
         filename="${PATHNAMES[index]}"
      fi

      true > clang_format_report.txt
      true > clang_tidy_report.txt

      echo "Performing checkup on $filename"
      # echo "incoming changed lines: $(get_patch_info $index)"

      if [ "$TIDY_CHECKS" == "" ]
      then
         clang-tidy-"$CLANG_VERSION" "$filename" >> clang_tidy_report.txt
      else
         clang-tidy-"$CLANG_VERSION" -checks="$TIDY_CHECKS" "$filename" >> clang_tidy_report.txt
      fi
      clang-format-"$CLANG_VERSION" -style="$FMT_STYLE" --dry-run "$filename" 2> clang_format_report.txt

      if [[ $(wc -l < clang_tidy_report.txt) -gt 0 ]]
      then
         PAYLOAD_TIDY+=$"### ${PATHNAMES[index]}"
         PAYLOAD_TIDY+="$FENCES"
         sed -i "s|$GITHUB_WORKSPACE/||g" clang_tidy_report.txt
         # cat clang_tidy_report.txt
         PAYLOAD_TIDY+=$(cat clang_tidy_report.txt)
         PAYLOAD_TIDY+="$FENCES"
      fi

      if [[ $(wc -l < clang_format_report.txt) -gt 0 ]]
      then
         if [ "$OUTPUT" == "" ]
         then
            OUTPUT=$'<!-- cpp linter action -->\n## Run `clang-format` on the following files\n'
         fi
         OUTPUT+="- [ ] ${PATHNAMES[index]}"$'\n'
      fi
   done

   if [ "$PAYLOAD_TIDY" != "" ]; then
      OUTPUT+=$'\n---\n## Output from `clang-tidy`\n'
      OUTPUT+="$PAYLOAD_TIDY"
   fi

   echo "OUTPUT is:"
   echo "$OUTPUT"
}

###################################################
# POST action's results using REST API
###################################################
post_results() {
   # check for access token (ENV VAR needed for git API calls)
   if [[ -z "$GITHUB_TOKEN" ]]
   then
      set_exit_code "1"
      echo "The GITHUB_TOKEN is required."
      exit "$EXIT_CODE"
   fi

   COMMENTS_URL=$(jq -r .pull_request.comments_url "$GITHUB_EVENT_PATH")
   COMMENT_COUNT=$(jq -r .comments "$GITHUB_EVENT_PATH")
   if [[ "$GITHUB_EVENT_NAME" == "push" ]]
   then
      COMMENTS_URL="$FILES_LINK/comments"
      COMMENT_COUNT=$(jq -r .commit.comment_count .cpp_linter_action_changed_files.json)
   fi
   echo "COMMENTS_URL: $COMMENTS_URL"
   echo "Number of Comments = $COMMENT_COUNT"
   if [[ $COMMENT_COUNT -gt 0 ]]
   then
      # get the list of comments
      curl "$COMMENTS_URL" > ".comments.json"
   fi
   PAYLOAD=$(echo '{}' | jq --arg body "$OUTPUT" '.body = $body')

   # creating PR comments is the same API as creating issue. Creating commit comments have more optional parameters (but same required API)
   curl -s -S -H "Authorization: token $GITHUB_TOKEN" --header "Content-Type: application/vnd.github.VERSION.text+json" "$COMMENTS_URL" --data "$PAYLOAD"
}

###################################################
# The main body of this script (all function calls)
###################################################
# for local testing (without docker):
#  1. Set the env var GITHUB_EVENT_NAME to "push" or "pull_request"
#  2. Download and save the event's payload (in JSON) to a file named ".cpp_linter_action_changed_files.json".
#       See the FILES_LINK variable in the get_list_of_changed_files() function for the event's payload.
#  3. Comment out the following calls to `get_list_of_changed_files` & `post_results` functions
#  4. Run this script using `./run_checks.sh <style> <extensions> <tidy checks> <relative working Dir>`
###################################################

get_list_of_changed_files
extract_changed_files_info
filter_out_non_source_files
verify_files_are_present
capture_clang_tools_output
set_exit_code
post_results
