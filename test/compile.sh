clang-12 -emit-llvm -fno-unroll-loops -fno-discard-value-names -O3 -o kernel.bc -c 1113IFELMY.cpp
# clang-12 -emit-llvm -fno-unroll-loops -O3 -o kernel.bc -c IFELtest.cpp
#llvm-dis fir.bc -o fir.ll
