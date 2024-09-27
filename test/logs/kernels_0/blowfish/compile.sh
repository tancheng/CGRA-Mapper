clang-3.8 -emit-llvm -O3 -fno-unroll-loops -o bf.bc -c bf_test.c
#llvm-dis bf.bc -o bf.ll
