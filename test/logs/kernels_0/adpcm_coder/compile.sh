clang -emit-llvm -O3 -fno-unroll-loops -o adpcm.bc -c adpcm.c
#llvm-dis fir.bc -o fir.ll
