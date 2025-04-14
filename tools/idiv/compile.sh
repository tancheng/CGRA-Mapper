clang-12 -emit-llvm -O3 -fno-unroll-loops -fno-vectorize -o idiv_test.bc -c idiv_test.cpp
# sed -i 's/\("testingOpcodeOffset"[[:space:]]*:[[:space:]]*\)0,/\12,/' param.json