#!/bin/bash

FILES_LINK=`jq -r '.pull_request._links.self.href' "$GITHUB_EVENT_PATH"`/files
echo "Files = $FILES_LINK"

curl $FILES_LINK > files.json
FILES_URLS_STRING=`jq -r '.[].raw_url' files.json`

readarray -t URLS <<<"$FILES_URLS_STRING"

echo "File names: $URLS"

mkdir files
cd files
for i in "${URLS[@]}"
do
   echo "Downloading $i"
   curl -LOk --remote-name $i 
done

echo "Files downloaded!"
echo "Performing checkup:"

mkdir build
cd build
cmake .. -DCMAKE_EXPORT_COMPILE_COMMANDS=ON && make -j4
clang-tidy ../*.cpp -checks=boost-*,bugprone-*,performance-*,readability-*,portability-*,modernize-*,clang-analyzer-cplusplus-#*,clang-analyzer-*,cppcoreguidelines-* -p=build
