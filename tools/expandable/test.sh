#!/bin/bash

# 生成原始版本的 trace.log
python main.py --old-new=0 | tee original.log

# 生成重构版本的 trace.log
python main.py --old-new=1 | tee refactored.log

# 比较两个文件是否完全一致
if diff -q original.log refactored.log >/dev/null; then
    echo "✅ 重构前后输出一致"
    exit 0
else
    echo "❌ 重构后输出发生变化！请检查差异："
    diff -u original.log refactored.log | head -n 20  # 只显示前20行差异
    exit 1
fi