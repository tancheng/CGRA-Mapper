icmpbr=$(grep -o 'icmpbr' dfg.json | wc -l)
phiadd=$(grep -o 'phiadd' dfg.json | wc -l)
fp2fx=$(grep -o 'fp2fx' dfg.json | wc -l)
faddmuladd=$(grep -o 'faddmuladd' dfg.json | wc -l)
if [ "$icmpbr" -eq 1 ] && [ "$phiadd" -eq 1 ] && [ "$fp2fx" -eq 1 ] && [ "$faddmuladd" -eq 1 ]; then
    echo "Nonlinear Test Pass!"
else
    echo "Nonlinear Test Fail! icmpbr, phiadd, fp2fx, faddmuladd should be 1, but got $icmpbr, $phiadd, $fp2fx, $faddmuladd."
    exit 1
fi

