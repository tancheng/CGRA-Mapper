clang-12 -emit-llvm -O3 -fno-unroll-loops -Rpass-analysis=loop-vectorize -o kernel.bc -c bicg.c
llvm-dis-12 kernel.bc -o kernel.ll
