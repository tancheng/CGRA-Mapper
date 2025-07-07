mapping_fail=$(grep -ao '\[Mapping Fail' trace.log | wc -l)
if [ "$mapping_fail" -eq 1 ]; then
    echo "Early Exit Test Pass!"
else
    echo "Early Exit Test Fail! mapping_fail should be 1, but got $mapping_fail"
    exit 1
fi
