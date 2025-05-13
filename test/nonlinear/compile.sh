clang-12 -emit-llvm -O3 -fno-unroll-loops -fno-vectorize -o nonlinear_test.bc -c nonlinear_test.cpp
clang-12 -O3 -emit-llvm -fno-vectorize -fno-unroll-loops nonlinear_test.cpp -S -o kernel.ll