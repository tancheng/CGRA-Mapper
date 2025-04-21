mapping_success=$(grep -ao '\[Mapping Success\]' trace.log | wc -l)
expandable_enabled=$(grep -ao '\[ExpandableII' trace.log | wc -l)
echo "mapping_success: $mapping_success"
echo "expandable_enabled: $expandable_enabled"
if [ "$mapping_success" -eq 1 ] && [ "$expandable_enabled" -eq 1 ]; then
    echo "Expandable Mapping Test Pass!"
else
    echo "Expandable Mapping Test Fail!"
    exit 1
fi

