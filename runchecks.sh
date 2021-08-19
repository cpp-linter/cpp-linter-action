#!/bin/bash

if [[ -z "$GITHUB_TOKEN" ]]; then
	echo "The GITHUB_TOKEN is required."
	exit 1
fi

args=("$@")
FMT_STYLE=${args[0]}
IFS=',' read -r -a FILE_EXT_LIST <<< "${args[1]}"

FILES_LINK=`jq -r '.pull_request._links.self.href' "$GITHUB_EVENT_PATH"`/files
echo "Files = $FILES_LINK"

curl $FILES_LINK > files.json
FILES_URLS_STRING=`jq -r '.[].raw_url' files.json`

readarray -t URLS <<<"$FILES_URLS_STRING"

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
  fi
done

echo "File names: ${URLS[*]}"
mkdir files
cd files
for i in "${URLS[@]}"
do
   echo "Downloading $i"
   curl -LOk --remote-name $i
done

echo "Files downloaded!"
echo "Performing checkup:"
clang-tidy --version

for i in "${URLS[@]}"
do
   filename=`basename $i`
   clang-tidy $filename -checks=boost-*,bugprone-*,performance-*,readability-*,portability-*,modernize-*,clang-analyzer-cplusplus-*,clang-analyzer-*,cppcoreguidelines-* >> clang-tidy-report.txt
   clang-format -style="$FMT_STYLE" --dry-run -Werror "$filename" || echo "File: $filename not formatted!" >> clang-format-report.txt
done

PAYLOAD_TIDY=`cat clang-tidy-report.txt`
PAYLOAD_FORMAT=`cat clang-format-report.txt`
COMMENTS_URL=$(cat $GITHUB_EVENT_PATH | jq -r .pull_request.comments_url)

echo $COMMENTS_URL
echo "Clang-tidy errors:"
echo $PAYLOAD_TIDY
echo "Clang-format errors:"
echo $PAYLOAD_FORMAT

if [ "$PAYLOAD_TIDY" != "" ]; then
   OUTPUT=$'**CLANG-TIDY WARNINGS**:\n'
   OUTPUT+=$'\n```\n'
   OUTPUT+="$PAYLOAD_TIDY"
   OUTPUT+=$'\n```\n'
fi

if [ "$PAYLOAD_FORMAT" != "" ]; then
   OUTPUT=$'**CLANG-FORMAT WARNINGS**:\n'
   OUTPUT+=$'\n```\n'
   OUTPUT+="$PAYLOAD_FORMAT"
   OUTPUT+=$'\n```\n'
fi

echo "OUTPUT is: \n $OUTPUT"

PAYLOAD=$(echo '{}' | jq --arg body "$OUTPUT" '.body = $body')

curl -s -S -H "Authorization: token $GITHUB_TOKEN" --header "Content-Type: application/vnd.github.VERSION.text+json" --data "$PAYLOAD" "$COMMENTS_URL"

EXIT_CODE=0
if [ "$PAYLOAD_FORMAT" != "" && "$PAYLOAD_TIDY" != "" ]
then
  EXIT_CODE=1
fi

echo "::set-output name=checks-failed::$(echo $EXIT_CODE)"
