#!/bin/bash
jq --raw-output . "$GITHUB_EVENT_PATH"
#mkdir build
#cd build
#cmake .. -DCMAKE_EXPORT_COMPILE_COMMANDS=ON && make -j4
#clang-tidy ../*.cpp -checks=boost-*,bugprone-*,performance-*,readability-*,portability-*,modernize-*,clang-analyzer-cplusplus-#*,clang-analyzer-*,cppcoreguidelines-* -p=$PWD

