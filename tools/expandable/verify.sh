mapping_success=$(grep -o '\[Mapping Success\]' trace.log | wc -l)
expandable_enabled=$(grep -o '\[ExpandableII' trace.log | wc -l)
if [ "$mapping_success" -eq 1 ] && [ "$expandable_enabled" -eq 1 ]; then
    echo "Expandable Mapping Test Pass!"
else
    echo "Expandable Mapping Test Fail!"
    exit 1
fi

