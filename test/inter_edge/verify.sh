exist_inter_edge=$(grep -o 'edge \[color=green\]' _Z6kernelPfS_S_.dot | wc -l)
if [ "$exist_inter_edge" -eq 1 ]; then
    echo "exist inter edge, inter edge test pass!"
else
    echo "no inter edge, inter edge test fail!"
    exit 1
fi