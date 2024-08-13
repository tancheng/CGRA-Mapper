clang -emit-llvm -fno-unroll-loops -O3 -o combineRelu.bc -c combineRelu.c
#llvm-dis fir.bc -o fir.ll
