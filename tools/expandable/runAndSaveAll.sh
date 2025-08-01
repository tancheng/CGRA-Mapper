#!/bin/bash

for ((i=1; i<=6; i++)); do
    python main.py --old-new=$i | tee traceALL${i}.log
done