clang-12 -emit-llvm -O3 -fno-unroll-loops -fno-vectorize -o kernel.bc -c kernel.cpp
#llvm-dis fir.bc -o fir.ll
