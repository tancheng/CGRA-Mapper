
exclusive_dfg_count=$(grep -o 'id' exclusive_dfg.json | wc -l)
distributed_dfg_count=$(grep -o 'id' distributed_dfg.json | wc -l)
inclusive_dfg_count=$(grep -o 'id' inclusive_dfg.json | wc -l)
if [ "$exclusive_dfg_count" -neq 11 ]; then
    echo "Multi-Cycle Test Failed! The count of DFG nodes in the exclusive strategy shoule be 11, but got $exclusive_dfg_count."
    exit 1
if [ "$inclusive_dfg_count" -neq 11 ]; then
    echo "Multi-Cycle Test Failed! The count of DFG nodes in the inclusive strategy shoule be 11, but got $inclusive_dfg_count."
    exit 1
if [ "$distributed_dfg_count" -neq 16 ]; then
    echo "Multi-Cycle Test Failed! The count of DFG nodes in the distributed strategy shoule be 16, but got $distributed_dfg_count."
    exit 1
else
    echo "Multi-Cycle Test Pass!"
fi