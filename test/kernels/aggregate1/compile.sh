clang -emit-llvm -fno-unroll-loops -O3 -o aggregate.bc -c aggregate.c
#llvm-dis fir.bc -o fir.ll
