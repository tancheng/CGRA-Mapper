#!/bin/bash

# kernelName = /WORK_REPO/CGRA-Flow/CGRA-Mapper/test/IFELtest.cpp

cd ../build
make
cd ../test
# clang-12 -emit-llvm -fno-unroll-loops -O3 -o kernel.bc -c IFELtest.cpp
# clang-12 -O3 -emit-llvm IFELtest.cpp -S -o kernel.ll
opt-12 -load ../build/src/libmapperPass.so -mapperPass kernel.bc | tee kernel.log
# dot -Tpng _Z11adpcmkerneliiPi.dot -o kernel.png
