cmake_minimum_required(VERSION 3.1)

#if(POLICY CMP0025)
#  cmake_policy(SET CMP0025 NEW)
#endif()

find_package(LLVM REQUIRED CONFIG)
list(APPEND CMAKE_MODULE_PATH "${LLVM_CMAKE_DIR}")
include(AddLLVM)
# LLVM 19's headers require C++17 (std::is_class_v, std::optional, std::size,
# ...); upstream pinned 14 for LLVM 12.  See PORT.md.
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
add_definitions(${LLVM_DEFINITIONS})
include_directories(${LLVM_INCLUDE_DIRS})
link_directories(${LLVM_LIBRARY_DIRS})

add_subdirectory(src)  # Use your pass directory here.
