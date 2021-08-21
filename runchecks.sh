#!/bin/bash

# global varibales
EXIT_CODE="0"
PAYLOAD_TIDY=""
FENCES=$'\n```\n'
OUTPUT=$'## Run `clang-format` on the following files\n'
URLS=""
PATHNAMES=""
declare -a PATCHES

# alias CLI args
args=("$@")
FMT_STYLE=${args[0]}
IFS=',' read -r -a FILE_EXT_LIST <<< "${args[1]}"
TIDY_CHECKS="${args[2]}"
CLANG_VERSION="${args[3]}"

cd "${args[4]}"

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

   # use git REST API payload
   if [[ "$GITHUB_EVENT_NAME" == "push" ]]
   then
      FILES_LINK="$GITHUB_API_URL/repos/$GITHUB_REPOSITORY/commits/$GITHUB_SHA"
   elif [[ "$GITHUB_EVENT_NAME" == "pull_request" ]]
   then
      FILES_LINK=`jq -r '.pull_request._links.self.href' "$GITHUB_EVENT_PATH"`/files
   fi

   # download files list (another json containing files' names, URLS, & diffs/patches)
   echo "Fetching files list from $FILES_LINK"
   curl $FILES_LINK > .cpp_linter_action_changed_files.json
}

###################################################
# extract info from downloaded JSON file
###################################################
extract_changed_files_info() {
   # pull_request events have a slightly different JSON format than push events
   JSON_FILES="."
   if [[ "$GITHUB_EVENT_NAME" == "push" ]]
   then
      JSON_FILES=".files"
   fi
   FILES_URLS_STRING=`jq -r "$JSON_FILES[].raw_url" .cpp_linter_action_changed_files.json`
   FILES_NAMES_STRING=`jq -r "$JSON_FILES[].filename" .cpp_linter_action_changed_files.json`
   PATCHED_STATUS_STRING=`jq -r "$JSON_FILES[].status" .cpp_linter_action_changed_files.json`

   # convert json info to arrays
   readarray -t URLS <<<"$FILES_URLS_STRING"
   readarray -t PATHNAMES <<<"$FILES_NAMES_STRING"
   readarray -t FILE_STATUS <<<"$PATCHED_STATUS_STRING"

   # patches are multiline strings. Thus they need special attention because of the '\n' used within.
   for index in ${!URLS[@]}
   do
      # we only need the first line stating the line numbers changed (ie "@@ -1,5 +1,5 @@"")
      patched_lines=$(jq -r -c "$JSON_FILES[$index].patch" .cpp_linter_action_changed_files.json)
      PATCHES[$index]=$(echo "$patched_lines" | sed '1,1!d' | sed 's;@@ ;;' | sed 's; @@;;')
      # if there is no patch field, then jq returns null
      if [[ "${PATCHES[index]}" == "null" ]]
      then
         # Fetch the status of the file in the commit. Handle 'renamed' & 'deleted' as edgde cases
         echo "${PATHNAMES[index]} was ${FILE_STATUS[index]}"
         if [[ "${FILE_STATUS[index]}" == "renamed" ]]
         then
            PATCHES[$index]="*"
         elif [[ "${FILE_STATUS[index]}" == "deleted" ]]
         then
            PATCHES[$index]="0"
         fi
      fi
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
         unset -v "FILE_STATUS[index]"
         unset -v "PATCHES[index]"
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
# Download the files if not present
# This function assumes that the working directory is the root of the invoking repo.
# Note that all github actions are run in the environment variable GITHUB_WORKSPACE
###################################################
verify_files_are_present() {
   # URLS, PATHNAMES, & PATCHES are parallel arrays
   for index in ${!PATHNAMES[@]}
   do
      if [[ ! -f "${PATHNAMES[index]}" ]]
      then
         echo "Downloading ${URLS[index]}"
         curl --location --insecure --remote-name "${URLS[index]}"
      fi
   done
}

###################################################
# execute clang-tidy/format & assemble a unified OUTPUT
###################################################
capture_clang_tools_output() {
   clang-tidy --version

   for index in "${!URLS[@]}"
   do
      filename=`basename ${URLS[index]}`
      if [[ -f "${PATHNAMES[index]}" ]]
      then
         filename="${PATHNAMES[index]}"
      fi
      echo "Performing checkup on $filename"
      echo "Patched: ${PATCHES[index]}"

      > clang_format_report.txt
      > clang_tidy_report.txt

      clang-tidy-"$CLANG_VERSION" "$filename" -checks="$TIDY_CHECKS" >> clang_tidy_report.txt
      clang-format-"$CLANG_VERSION" -style="$FMT_STYLE" --dry-run "$filename" 2> clang_format_report.txt

      if [[ $(wc -l < clang_tidy_report.txt) -gt 0 ]]
      then
         PAYLOAD_TIDY+=$"### ${PATHNAMES[index]}"
         PAYLOAD_TIDY+="$FENCES"
         sed -i "s|$GITHUB_WORKSPACE/||g" clang_tidy_report.txt
         # cat clang_tidy_report.txt
         PAYLOAD_TIDY+=`cat clang_tidy_report.txt`
         PAYLOAD_TIDY+="$FENCES"
      fi
      if [[ $(wc -l < clang_format_report.txt) -gt 0 ]]
      then
         OUTPUT+="- [ ] ${PATHNAMES[index]}"$'\n'
      fi
   done

   if [ "$PAYLOAD_TIDY" != "" ]; then
      OUTPUT+=$'\n---\n## Output from `clang-tidy`\n'
      OUTPUT+="$PAYLOAD_TIDY"
   fi

   # echo "OUTPUT is:"
   # echo "$OUTPUT"
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

   COMMENTS_URL=$(cat $GITHUB_EVENT_PATH | jq -r .pull_request.comments_url)
   if [[ "$GITHUB_EVENT_NAME" == "push" ]]
   then
      COMMENTS_URL="$FILES_LINK/comments"
   fi

   echo "COMMENTS_URL = $COMMENTS_URL"

   PAYLOAD=$(echo '{}' | jq --arg body "$OUTPUT" '.body = $body')

   # creating PR comments is the same API as creating issue. Creating commit comments have more optional parameters (but same required API)
   curl -s -S -H "Authorization: token $GITHUB_TOKEN" --header "Content-Type: application/vnd.github.VERSION.text+json" "$COMMENTS_URL" --data "$PAYLOAD"
}

###################################################
# The main body of this script (all function calls)
###################################################

# get_list_of_changed_files
extract_changed_files_info
filter_out_non_source_files
verify_files_are_present
capture_clang_tools_output
set_exit_code
# post_results
