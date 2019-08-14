add_library(cgraPass MODULE
    # List your source files here.
    cgraPass.cpp
    DFG.h
    DFG.cpp
    CGRANode.h
    CGRANode.cpp
    CGRALink.h
    CGRALink.cpp
    CGRA.h
    CGRA.cpp
    Mapper.h
    Mapper.cpp
)

# Use C++11 to compile our pass (i.e., supply -std=c++11).
target_compile_features(cgraPass PRIVATE cxx_range_for cxx_auto_type)

# LLVM is (typically) built with no C++ RTTI. We need to match that;
# otherwise, we'll get linker errors about missing RTTI data.
set_target_properties(cgraPass PROPERTIES
    COMPILE_FLAGS "-fno-rtti"
)

# Get proper shared-library behavior (where symbols are not necessarily
# resolved when the shared library is linked) on OS X.
if(APPLE)
    set_target_properties(cgraPass PROPERTIES
        LINK_FLAGS "-undefined dynamic_lookup"
    )
endif(APPLE)
