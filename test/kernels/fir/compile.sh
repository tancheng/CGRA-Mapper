clang-12 -emit-llvm -fno-unroll-loops -O3 -o kernel.bc -c fir.cpp
llvm-dis-12 kernel.bc -o kernel.ll
opt-12 --loop-unroll --unroll-count=4 kernel.bc -o kernel_unroll.bc
llvm-dis-12 kernel_unroll.bc -o kernel_unroll.ll
