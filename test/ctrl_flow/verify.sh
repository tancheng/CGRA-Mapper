phiaddcmpbr=$(grep -o 'phiaddcmpbr' dfg.json | wc -l) # pattern input of combineForIter
phiadd=$(grep -o '\bphiadd\b' dfg.json | wc -l) # pattern fused by combineForUnroll
if [ "$phiaddcmpbr" -eq 1 ] && [ "$phiadd" -eq 1 ]; then
    echo "Control Flow Test Pass!"
else
    echo "Control Flow Test Fail! phiaddcmpbr, phiadd should be 1, but got $phiaddcmpbr, $phiadd"
    exit 1
fi

