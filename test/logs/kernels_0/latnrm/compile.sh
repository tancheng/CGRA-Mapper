clang-12 -emit-llvm -O3 -fno-unroll-loops -o kernel.bc -c latnrm.c
llvm-dis-12 kernel.bc -o kernel.ll
