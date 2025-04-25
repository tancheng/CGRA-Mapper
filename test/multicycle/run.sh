cat param_exclusive.json > param.json 
opt-12 -load ../../build/src/libmapperPass.so -mapperPass multicycle_test.bc
mv dfg.json exclusive_dfg.json
cat param_distributed.json > param.json 
opt-12 -load ../../build/src/libmapperPass.so -mapperPass multicycle_test.bc
mv dfg.json distributed_dfg.json
cat param_inclusive.json > param.json 
opt-12 -load ../../build/src/libmapperPass.so -mapperPass multicycle_test.bc
mv dfg.json inclusive_dfg.json