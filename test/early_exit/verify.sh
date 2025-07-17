failed_node=$(grep -ao 'No available CGRA node for DFG node [^[:space:]]*' trace.log | head -1 | awk '{print $NF}')
mapping_fail=$(grep -ao '\[Mapping Fail' trace.log | wc -l)
if [ "$mapping_fail" -eq 1 ]; then
    echo "First detected mapping failure node: ${failed_node}"
    echo "Early Exit Test Pass!"
else
    echo "Early Exit Test Fail! mapping_fail should be 1, but got $mapping_fail"
    exit 1
fi
