#!/usr/bin/env bash

mapping_fail=$(grep -ao '\[Mapping Fail' trace.log | wc -l)
missing_line=$(grep -ao '\[canMap\] Missing functional units' trace.log | wc -l)

if [ "$mapping_fail" -eq 1 ] && [ "$missing_line" -ge 1 ]; then
    echo "Early Exit Test Pass! Test early exits because of missing opcodes"
else
    echo "Early Exit Test Fail!"
    echo "mapping_fail: $mapping_fail"
    echo "missing_line: $missing_line"
    exit 1
fi