clang -emit-llvm -fno-unroll-loops -O3 -o compress.bc -c compress.cpp
#llvm-dis fir.bc -o fir.ll
