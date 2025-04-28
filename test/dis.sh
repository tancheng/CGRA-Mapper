clang-12 -O3 -emit-llvm -fno-vectorize -fno-unroll-loops conv.c -S -o kernel.ll
# clang-12 -O3 -emit-llvm -funroll-loops -mllvm -unroll-count=2 conv.c -S -o kernel.ll
#clang-12 -O3 -emit-llvm conv.c -S -o kernel.ll
