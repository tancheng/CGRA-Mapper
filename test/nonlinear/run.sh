opt-12 -load ../../build/src/libmapperPass.so -mapperPass nonlinear_test.bc
# dot -Tpng _Z6kernelPfS_.dot -o kernel.png
# clang-12 -O3 -emit-llvm -fno-unroll-loops -fno-vectorize nonlinear_test.cpp -S -o nonlinear_test.ll