# original test
origin_mapping_ii=$(grep -aoP '\[Mapping II: \K[^]]+' trace.log)
# ctrl_flow test
sed -i 's/\("fusionStrategy"[[:space:]]*:[[:space:]]*\)\[\]/\1["ctrl_flow"]/' param.json
opt-12 -load ../../build/src/libmapperPass.so -mapperPass kernel.bc | tee trace.log
phiaddcmpbr=$(grep -o 'phiaddcmpbr' dfg.json | wc -l) # pattern input of combineForIter
phiadd=$(grep -o '\bphiadd\b' dfg.json | wc -l) # pattern fused by combineForUnroll
fused_mapping_ii=$(grep -aoP '\[Mapping II: \K[^]]+' trace.log)
if [ "$phiaddcmpbr" -eq 1 ] && [ "$phiadd" -eq 1 ] && [ "$origin_mapping_ii" -eq 4 ] && [ "$fused_mapping_ii" -eq 1 ]; then
    echo "Control Flow Test Pass!"
else
    echo "Control Flow Test Fail! phiaddcmpbr, phiadd, origin_mapping_ii, fused_mapping_ii should be 1, 1, 4, 1.
    but got $phiaddcmpbr, $phiadd, $origin_mapping_ii, $fused_mapping_ii"
    exit 1
fi
