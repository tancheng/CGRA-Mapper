# original test
vaddOrigin=$(grep -o 'vadd' dfg.json | wc -l)
# vector test
clang-12 -emit-llvm -O3 -fno-unroll-loops -O3 -mllvm -force-vector-width=4 -o kernel.bc -c conv.c
opt-12 -load ../../build/src/libmapperPass.so -mapperPass kernel.bc
vadd=$(grep -o 'vadd' dfg.json | wc -l)
vload=$(grep -o 'vload' dfg.json | wc -l)
vmul=$(grep -o 'vmul' dfg.json | wc -l)
vphi=$(grep -o 'vphi' dfg.json | wc -l)
if [ "$vaddOrigin" -eq 0 ] && [ "$vadd" -eq 1 ] && [ "$vload" -eq 2 ] && [ "$vmul" -eq 1 ] && [ "$vphi" -eq 1 ]; then
    echo "Vectorization Test Pass!"
else
    echo "Vectorization Test Fail! vaddOrigin should be 0. vadd, vmul, vphi should be 1 and vload should be 2, but got $vaddOrigin, $vadd, $vmul, $vphi, $vload."
    exit 1
fi

