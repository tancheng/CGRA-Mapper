#!/usr/bin/env bash
# source /WORK_REPO/venv/bin/activate

mkdir ./tmp
mkdir ./result
mkdir ./fig

python main.py | tee trace.log

cat trace.log
