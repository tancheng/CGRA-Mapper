clang-12 -emit-llvm -O3 -fno-unroll-loops -o kernel.bc -c fft.c
llvm-dis-12 kernel.bc -o kernel.ll
opt-12 --loop-unroll --unroll-count=2 kernel.bc -o kernel_unroll.bc
#clang-12 -emit-llvm -O3 -fno-unroll-loops -Rpass-analysis=loop-vectorize -o kernel.bc -c fft.c
llvm-dis-12 kernel_unroll.bc -o kernel_unroll.ll
