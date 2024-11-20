echo "___________________________________________________________________\n"
cat dfg.json 
echo "___________________________________________________________________\n"
icmpbr=$(grep -o 'sdiv' ./dfg.json | wc -l)
echo "icmpbr", $icmpbr

count=$(grep -o 'sdiv' dfg.json | wc -l)
if [ "$(grep -o 'sdiv' dfg.json | wc -l)" -eq 4 ]; then
    echo "Idiv Test Pass!"
else
    echo "Idiv Test Fail! The count of sdiv should be 4, but got 0."
    exit 1
fi