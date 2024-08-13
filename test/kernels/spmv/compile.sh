clang-12 -emit-llvm -O3 -fno-unroll-loops -o kernel.bc -c spmv.c
llvm-dis-12 kernel.bc -o kernel.ll
