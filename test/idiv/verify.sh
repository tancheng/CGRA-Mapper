#!/bin/bash

count=$(grep -o 'sdiv' dfg.json | wc -l)
if [ "$count" -eq 4 ]
then
    echo "Idiv Test Pass!"
else
    echo "Idiv Test Fail! The count of sdiv should be 4, but got 0."
    exit 1
fi