import sys
import re

def main():
    # 定义需要匹配的行的前缀
    prefixes = [
        r'Total idle duration is',
        r'Simulation completed\. Kernel latencies:',
        r'CGRA utilization:',
        r'overall latency:',
        r'overall execution',
        r'overall waiting_time_nolap',
        r'=== At time'
    ]

    # 构建正则表达式模式
    patterns = [re.compile(r'^' + prefix) for prefix in prefixes]

    # 用于存储基准值（第一组数据）
    base_utilization = None
    base_latency = None
    base_execution = None
    base_waiting = None

    # 读取输入文件或标准输入
    if len(sys.argv) > 1:
        filename = sys.argv[1]
        try:
            with open(filename, 'r') as file:
                lines = file.readlines()
        except FileNotFoundError:
            print(f"错误: 文件 '{filename}' 不存在。", file=sys.stderr)
            sys.exit(1)
    else:
        lines = sys.stdin.readlines()

    # 查找并输出匹配的行，同时计算加速比
    for line in lines:
        line = line.rstrip('\n')
        for pattern in patterns:
            if pattern.search(line):
                print(line)

                # 处理 CGRA utilization 行
                if line.startswith('CGRA utilization:'):
                    # 提取数值
                    util_value = float(line.split(': ')[1])
                    # 如果是第一组数据，保存为基准值
                    if base_utilization is None:
                        base_utilization = util_value
                        speedup = 1.0
                    else:
                        # 后续数据与基准值计算加速比
                        speedup = util_value / base_utilization
                    print(f"utilization speedup = {speedup:.2f}")

                # 处理 overall latency 行
                elif line.startswith('overall latency:'):
                    latency_value = int(line.split(': ')[1])
                    if base_latency is None:
                        base_latency = latency_value
                        speedup = 1.0
                    else:
                        speedup = base_latency /latency_value
                    print(f"latency speedup = {speedup:.2f}")

                # 处理 overall execution 行
                elif line.startswith('overall execution:'):
                    exec_value = int(line.split(': ')[1])
                    if base_execution is None:
                        base_execution = exec_value
                        speedup = 1.0
                    else:
                        speedup =  base_execution / exec_value
                    print(f"execution speedup = {speedup:.2f}")

                # 处理 overall waiting 行
                elif line.startswith('overall waiting_time_nolap:'):
                    wait_value = int(line.split(': ')[1])
                    if base_waiting is None:
                        base_waiting = wait_value
                        speedup = 1.0
                    else:
                        speedup =  base_waiting / wait_value if wait_value is not 0 else 0
                    print(f"waiting speedup = {speedup:.2f}")
                    print("===============================================")

                # 处理 CHECK TIME 行
                elif line.startswith('=== At time '):
                    #compelted_kernels = int(line.split(': ')[1])
                    # if base_waiting is None:
                    #     base_waiting = wait_value
                    #     speedup = 1.0
                    # else:
                    #     speedup =  base_waiting / wait_value if wait_value is not 0 else 0
                    # print(f"waiting speedup = {speedup:.2f}")
                    pass

                break

if __name__ == "__main__":
    main()