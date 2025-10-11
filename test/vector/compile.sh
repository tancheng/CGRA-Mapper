clang-12 -emit-llvm -O3 -fno-unroll-loops -O3 -fno-vectorize -o kernel.bc -c conv.c
# clang-12 -emit-llvm -O3 -fno-unroll-loops -O3 -mllvm -force-vector-width=4 -o kernel.bc -c conv.c
# llvm-dis-12 kernel.bc -o kernel.ll