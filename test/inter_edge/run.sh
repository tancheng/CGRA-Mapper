if command -v opt-12 >/dev/null 2>&1; then
    opt-12 -load ../../build/src/libmapperPass.so -mapperPass inter_edge_test.bc
else
    opt -load ../../build/src/libmapperPass.so -mapperPass inter_edge_test.bc
fi
