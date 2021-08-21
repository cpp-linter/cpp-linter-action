#!/bin/bash

EXIT_CODE="0"
PAYLOAD_TIDY=""
FENCES=$'\n```\n'
OUTPUT=$'## Run `clang-format` on the following files\n'

function set_exit_code () {
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

# check for access token (ENV VAR needed for git API calls)
if [[ -z "$GITHUB_TOKEN" ]]
then
	echo "The GITHUB_TOKEN is required."
   set_exit_code "1"
	exit "$EXIT_CODE"
fi

# parse CLI args
args=("$@")
FMT_STYLE=${args[0]}
IFS=',' read -r -a FILE_EXT_LIST <<< "${args[1]}"
TIDY_CHECKS="${args[2]}"
CLANG_VERSION="${args[3]}"

echo "GH_EVENT_PATH = $GITHUB_EVENT_PATH"
echo "processing $GITHUB_EVENT_NAME event"
# cat "$GITHUB_EVENT_PATH" | jq '.'

if [[ "$GITHUB_EVENT_NAME" == "push" ]]
then
   # get list of commits from the event's payload's url
   FILES_LINK="$GITHUB_API_URL/repos/$GITHUB_REPOSITORY/commits/$GITHUB_SHA"
elif [[ "$GITHUB_EVENT_NAME" == "pull_request" ]]
then
   # use git API payload
   FILES_LINK=`jq -r '.pull_request._links.self.href' "$GITHUB_EVENT_PATH"`/files
fi

# download files' name & URLS
echo "Fetching files list from $FILES_LINK"
curl $FILES_LINK > .cpp_linter_action_changed_files.json

# extract info from json
if [[ "$GITHUB_EVENT_NAME" == "push" ]]
then
   FILES_URLS_STRING=`jq -r '.files[].raw_url' .cpp_linter_action_changed_files.json`
   FILES_NAMES_STRING=`jq -r '.files[].filename' .cpp_linter_action_changed_files.json`
elif [[ "$GITHUB_EVENT_NAME" == "pull_request" ]]
then
   FILES_URLS_STRING=`jq -r '.[].raw_url' .cpp_linter_action_changed_files.json`
   FILES_NAMES_STRING=`jq -r '.[].filename' .cpp_linter_action_changed_files.json`
fi

# convert json info to arrays
readarray -t URLS <<<"$FILES_URLS_STRING"
readarray -t PATHNAMES <<<"$FILES_NAMES_STRING"

# exclude undesired files
for index in "${!URLS[@]}"
do
   is_supported=0
   for i in "${FILE_EXT_LIST[@]}"
   do
      if [[ ${URLS[index]} == *".$i" ]]
      then
         is_supported=1
      fi
   done

   if [ $is_supported == 0 ]
   then
      unset -v "URLS[index]"
      unset -v "PATHNAMES[index]"
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

for index in "${!URLS[@]}"
do
   if [[ ! -f "$GITHUB_WORKSPACE/${PATHNAMES[index]}" ]]
   then
      echo "Downloading ${URLS[index]}"
      curl -LOk --remote-name ${URLS[index]}
   fi
done

echo "Performing checkup:"
clang-tidy --version

for index in "${!URLS[@]}"
do
   filename=`basename ${URLS[index]}`
   if [[ -f "$GITHUB_WORKSPACE/${PATHNAMES[index]}" ]]
   then
      filename="$GITHUB_WORKSPACE/${PATHNAMES[index]}"
   fi

   > clang_format_report.txt
   > clang_tidy_report.txt
   CLANG_CONFIG="-checks=$TIDY_CHECKS"
   if [[ "$TIDY_CHECKS" == "" ]]
   then
      CLANG_CONFIG="--config"
   fi

   clang-tidy-"$CLANG_VERSION" "$filename" "$CLANG_CONFIG" -format-style="$FMT_STYLE" >> clang_tidy_report.txt
   clang-format-"$CLANG_VERSION" -style="$FMT_STYLE" --dry-run "$filename" 2> clang_format_report.txt
   echo "Current work dir: $(pwd)"
   if [[ $(wc -l < clang_tidy_report.txt) -gt 0 ]]
   then
      PAYLOAD_TIDY+=$"### ${PATHNAMES[index]}"
      PAYLOAD_TIDY+="$FENCES"
      sed -i "s|$GITHUB_WORKSPACE||g" clang_tidy_report.txt
      cat clang_tidy_report.txt
      PAYLOAD_TIDY+=`cat clang_tidy_report.txt`
      PAYLOAD_TIDY+="$FENCES"
   fi
   if [[ $(wc -l < clang_format_report.txt) -gt 0 ]]
   then
      OUTPUT+="- [ ] ${PATHNAMES[index]}"$'\n'
   fi
done

OUTPUT+=$'\n---\n## Output from `clang-tidy`\n'

COMMENTS_URL=$(cat $GITHUB_EVENT_PATH | jq -r .pull_request.comments_url)
if [[ "$GITHUB_EVENT_NAME" == "push" ]]
then
   COMMENTS_URL="$FILES_LINK/comments"
fi

echo "COMMENTS_URL = $COMMENTS_URL"

if [ "$PAYLOAD_TIDY" != "" ]; then
   OUTPUT+="$PAYLOAD_TIDY"
fi


set_exit_code

echo "OUTPUT is:"
echo "$OUTPUT"

PAYLOAD=$(echo '{}' | jq --arg body "$OUTPUT" '.body = $body')

# creating PR comments is the same API as creating issue. Creating commit comments have more optional parameters (but same required API)
curl -s -S -H "Authorization: token $GITHUB_TOKEN" --header "Content-Type: application/vnd.github.VERSION.text+json" "$COMMENTS_URL" --data "$PAYLOAD"
