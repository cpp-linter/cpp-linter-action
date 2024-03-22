cmake_minimum_required(VERSION 3.15)

# Set the project name to your project name
project(demo C CXX)

set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

add_executable(demo_app
    ${CMAKE_BINARY_SOURCE_DIR}demo.hpp
    ${CMAKE_BINARY_SOURCE_DIR}demo.cpp
)
target_include_directories(demo_app PUBLIC ${CMAKE_BINARY_SOURCE_DIR})
