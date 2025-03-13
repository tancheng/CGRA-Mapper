clang-12 -emit-llvm -fno-unroll-loops -O3 -o inter_edge_test.bc -c inter_edge_test.cpp
llvm-dis inter_edge_test.bc -o inter_edge_test.ll
# opt --loop-unroll --unroll-count=4 kernel.bc -o kernel_unroll.bc
# llvm-dis kernel_unroll.bc -o kernel_unroll.ll
