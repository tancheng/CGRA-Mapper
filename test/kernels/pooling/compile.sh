clang -emit-llvm -fno-unroll-loops -O3 -o pool.bc -c pool.c
#llvm-dis fir.bc -o fir.ll
