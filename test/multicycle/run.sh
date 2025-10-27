cat param_exclusive.json > param.json 
opt-12 -load ../../build/src/libmapperPass.so -mapperPass multicycle_test.bc | tee trace_exclusive.log
mv dfg.json exclusive_dfg.json
cat param_distributed.json > param.json 
opt-12 -load ../../build/src/libmapperPass.so -mapperPass multicycle_test.bc | tee trace_distributed.log
mv dfg.json distributed_dfg.json
cat param_inclusive.json > param.json 
opt-12 -load ../../build/src/libmapperPass.so -mapperPass multicycle_test.bc | tee trace_inclusive.log
mv dfg.json inclusive_dfg.json