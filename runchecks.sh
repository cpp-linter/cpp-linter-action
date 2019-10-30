#!/bin/bash

FILES_LINK="https://api.github.com/repos/smay1613/CITest/pulls/1/files"
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
clang-tidy --version
clang-tidy *.cpp -checks=boost-*,bugprone-*,performance-*,readability-*,portability-*,modernize-*,clang-analyzer-cplusplus-#*,clang-analyzer-*,cppcoreguidelines-*
