# clang-12 -emit-llvm -fno-unroll-loops -O3 -o kernel.bc -c kernel.cpp
clang-12 -emit-llvm -funroll-loops -mllvm -unroll-count=2 -O3 -o kernel.bc -c kernel.cpp
llvm-dis-12 kernel.bc -o kernel.ll
