#!/bin/bash

for ((i=2; i<=5; i++)); do
    python main.py --old-new=7$i | tee trace7${i}.log
done