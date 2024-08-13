clang -emit-llvm -O3 -o kernel.bc -c kernel.cpp
#clang -emit-llvm -fno-unroll-loops -O3 -o kernel.bc -c kernel.cpp
#llvm-dis fir.bc -o fir.ll
