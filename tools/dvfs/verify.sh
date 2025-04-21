#!/bin/bash
mapping_success=$(grep -o '\[Mapping Success\]' trace.log | wc -l)
dvfs_enabled=$(grep -o 'tile average DVFS frequency level' trace.log | wc -l)
dvfs_no_effect=$(grep -o 'tile average DVFS frequency level: 100%' trace.log | wc -l)
if [ "$mapping_success" -eq 1 ] && [ "$dvfs_enabled" -eq 1 ] && [ "$dvfs_no_effect" -eq 0 ]; then
    echo "DVFS Test Pass!"
else
    error_message="DVFS Test Fail! "
    if [ "$mapping_success" -ne 1 ]; then
        error_message+="mapping_success is not equal to 1. "
    fi
    if [ "$dvfs_enabled" -ne 1 ]; then
        error_message+="dvfs_enabled is not equal to 1. "
    fi
    if [ "$dvfs_no_effect" -ne 0 ]; then
        error_message+="dvfs_no_effect is not equal to 0. "
    fi
    echo "$error_message"
    exit 1
fi

