mapping_success=$(grep -o '[Mapping Success]' trace.log | wc -l)
dvfs_enabled=$(grep -o 'tile average DVFS frequency level' trace.log | wc -l)
dvfs_no_effect=$(grep -o 'tile average DVFS frequency level: 100%' trace.log | wc -l)
if [ "$mapping_success" -eq 1 ] && [ "$dvfs_enabled" -eq 1 ] && [ "$dvfs_no_effect" -eq 0 ]; then
    echo "DVFS Test Pass!"
else
    echo "DVFS Test Fail!"
    exit 1
fi

