clang-3.8 -emit-llvm -O3 -fno-unroll-loops -o susan.bc -c susan.c
#llvm-dis susan.bc -o susan.ll
