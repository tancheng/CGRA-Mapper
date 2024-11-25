clang -emit-llvm -fno-unroll-loops -O3 -o combine.bc -c combine.c
#llvm-dis fir.bc -o fir.ll
