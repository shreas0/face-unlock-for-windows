cmake_minimum_required(VERSION 3.15)
project(FaceUnlockProvider LANGUAGES C CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

add_library(FaceUnlockProvider SHARED
    FaceUnlockProvider.cpp
    FaceCredential.cpp
    helpers.cpp
    FaceUnlockProvider.def
    FaceUnlockProvider.h
    helpers.h
)

target_link_libraries(FaceUnlockProvider PRIVATE
    Secur32
    Crypt32
    Shlwapi
)

set_target_properties(FaceUnlockProvider PROPERTIES
    OUTPUT_NAME "FaceUnlockProvider"
    PREFIX ""
)
