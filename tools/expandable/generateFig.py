import pandas as pd
import matplotlib.pyplot as plt
import os
from typing import List, Dict, Any, Optional
import glob
import re

class SimulationDataAnalyzer:
    """模拟数据可视化分析工具"""

    def __init__(self, result_dir: str = './result'):
        """
        初始化分析器

        参数:
            result_dir (str): 结果文件所在目录，默认为'./result'
        """
        self.result_dir = result_dir
        self.data_cache = {}  # 缓存已读取的数据
        self.figure_config = {
            'figsize': (10, 6),
            'xlabel': '数据行索引',
            'ylabel': 'Total_Execution_duration',
            'title': '不同设置下 Total_Execution_duration 折线图',
            'show_legend': True,
            'output_path': None  # 若设置则保存图片而非显示
        }

    def load_data(self, kernel_case: str, csvname: str,
                  priority_boosting: int, num_cgras: int = 9) -> pd.DataFrame:
        """
        读取单个 CSV 文件的数据

        参数:
            kernel_case (str): 内核案例标识
            csvname (str): CSV 文件名标识
            priority_boosting (int): 优先级提升标识
            num_cgras (int): CGRA 数量

        返回:
            pd.DataFrame: 包含指定列的 DataFrame，或 None（文件不存在时）
        """
        file_path = os.path.join(
            self.result_dir,
            f'simulation_{kernel_case}_{csvname}.csv'
        )

        if not os.path.exists(file_path):
            print(f"文件不存在: {file_path}")
            return None

        # 读取指定列的数据
        try:
            df = pd.read_csv(file_path)
            required_columns = ['Total_Execution_duration', 'Overall_Case_Latency', 'CGRA_Utilization']

            # 检查所需列是否存在
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                raise ValueError(f"文件缺少必要的列: {', '.join(missing_columns)}")

            # 缓存数据
            cache_key = f"{kernel_case}_{csvname}"
            self.data_cache[cache_key] = df[required_columns]
            return self.data_cache[cache_key]

        except Exception as e:
            print(f"读取文件失败: {file_path}, 错误: {str(e)}")
            return None

    def batch_load_data(self, kernel_cases: List[str], csvnames: List[str],
                       priority_boosting: int, num_cgras: int = 9) -> Dict[str, pd.DataFrame]:
        """
        批量读取多个 CSV 文件的数据

        参数:
            kernel_cases (List[str]): 内核案例标识列表
            csvnames (List[str]): CSV 文件名标识列表
            priority_boosting (int): 优先级提升标识
            num_cgras (int): CGRA 数量

        返回:
            Dict[str, pd.DataFrame]: 缓存键到 DataFrame 的映射
        """
        for kernel_case in kernel_cases:
            for csvname in csvnames:
                self.load_data(kernel_case, csvname, priority_boosting, num_cgras)

        return self.data_cache

    def set_figure_config(self, **kwargs: Any) -> None:
        """
        设置图表配置

        参数:
            figsize (tuple): 图表大小，默认 (10, 6)
            xlabel (str): x轴标签
            ylabel (str): y轴标签
            title (str): 图表标题
            show_legend (bool): 是否显示图例
            output_path (str): 图片保存路径，若设置则保存而非显示
        """
        for key, value in kwargs.items():
            if key in self.figure_config:
                self.figure_config[key] = value
            else:
                print(f"忽略未知配置项: {key}")

    def generate_execution_duration_plot(self,
                                        data_keys: Optional[List[str]] = None,
                                        group_by: str = 'kernel_case',
                                        normalize: bool = True) -> None:
        """
        生成执行时间折线图

        参数:
            data_keys (List[str]): 要包含的缓存键列表，默认使用所有缓存数据
            group_by (str): 分组方式，支持 'kernel_case' 或 'csvname'
            normalize (bool): 是否对数据进行正则化，默认为 True
        """
        # 确定要使用的数据
        if data_keys is None:
            data_to_plot = self.data_cache
        else:
            data_to_plot = {key: self.data_cache[key] for key in data_keys if key in self.data_cache}

        if not data_to_plot:
            print("没有可用的数据进行绘图")
            return

        # 创建图表
        plt.figure(figsize=self.figure_config['figsize'])

        # 根据分组方式设置标签并绘图
        for key, df in data_to_plot.items():
            kernel_case, csvname = key.split('_', 1)
            label = kernel_case if group_by == 'kernel_case' else csvname

            # 获取执行时间数据
            execution_data = df['Total_Execution_duration']

            # 正则化数据（如果需要）
            if normalize:
                normalized_data = (execution_data - execution_data.min()) / (execution_data.max() - execution_data.min())
                if normalized_data.std() == 0:  # 处理所有值相同的情况
                    normalized_data = pd.Series([0.5] * len(execution_data), index=execution_data.index)
                plot_data = normalized_data
                y_label = f"Normalized {self.figure_config['ylabel']}"
            else:
                plot_data = execution_data
                y_label = self.figure_config['ylabel']

            plt.plot(
                plot_data.index,
                plot_data,
                label=f"{label} ({key})",
                marker='o',  # 添加标记点使数据更清晰
                alpha=0.7    # 设置透明度
            )

        # 设置图表属性
        plt.xlabel(self.figure_config['xlabel'])
        plt.ylabel(y_label)

        # 更新标题以反映是否使用了正则化
        title = self.figure_config['title']
        if normalize:
            title += " (Normalized)"
        plt.title(title)

        if self.figure_config['show_legend']:
            plt.legend()

        plt.grid(True, linestyle='--', alpha=0.7)  # 添加网格线
        plt.tight_layout()  # 确保布局紧凑

        # 保存或显示图表
        if self.figure_config['output_path']:
            plt.savefig(self.figure_config['output_path'])
            print(f"图表已保存至: {self.figure_config['output_path']}")
        else:
            plt.show()


# 初始化分析器
# analyzer = SimulationDataAnalyzer(result_dir='./result/')

# # 批量加载数据
# kernel_cases = ['1']
# csvnames = ['Baseline', 'csv2']
# for cases in kernel_cases:
#     for csvname in csvnames:
#         analyzer.batch_load_data(
#             kernel_cases=kernel_cases,
#             csvnames=csvnames,
#             priority_boosting=0
#         )

# # 自定义图表配置
# analyzer.set_figure_config(
#     title='不同内核案例的执行时间对比',
#     ylabel='总执行时间 (ms)',
#     figsize=(12, 7)
# )

# # 生成并显示图表（按 kernel_case 分组）
# analyzer.generate_execution_duration_plot(group_by='kernel_case')

# # 保存图表（按 csvname 分组）
# analyzer.set_figure_config(
#     output_path='./execution_comparison.png',
#     title='不同 CSV 配置的执行时间对比'
# )
# analyzer.generate_execution_duration_plot(group_by='csvname')



def combine_csv_files():
    # 定义期望的排序顺序（不包含数字前缀部分）
    order = [
        'Baseline',
        'NoBosting',
        'BostingScalar',
        'BostingScalarFuse',
        'BostingScalarFuseVector'
    ]

    # 创建排序键的映射，用于自定义排序
    order_map = {name: idx for idx, name in enumerate(order)}

    # 定义需要处理的指标列表及其对应的输出文件名
    metrics = [
        #{'column': 'Average_Execution_duration', 'output': 'execution_time.csv'},
        {'column': 'Overall_Case_Latency', 'output': 'overall_case_latency.csv'},

        {'column': 'checked_num_kernel', 'output': 'checked_num_kernel.csv'}
        # 可以在这里添加更多需要处理的指标
    ]

    # 获取当前目录下所有simulation开头的csv文件
    csv_files = glob.glob('./result/simulation_*.csv')

    if not csv_files:
        print("没有找到符合条件的CSV文件")
        return

    # 解析文件名，提取数字前缀和类型
    def parse_filename(filename):
        base_name = os.path.splitext(os.path.basename(filename))[0]
        # 提取类似"simulation_74_BostingScalarFuse"中的数字和类型部分
        match = re.match(r'simulation_(\d+)_(.+)', base_name)
        if match:
            num = int(match.group(1))
            type_name = match.group(2)
            return (num, type_name, filename)
        return (0, '', filename)  # 不符合命名规则的文件放最后

    # 解析所有文件
    parsed_files = [parse_filename(file) for file in csv_files]

    # 自定义排序函数：先按数字前缀排序，再按预定义的类型顺序排序
    def sort_key(item):
        num, type_name, file = item
        # 找到类型在预定义顺序中的位置，如果不在列表中则放在最后
        type_order = order_map.get(type_name, len(order))
        return (num, type_order)

    # 按自定义规则排序文件
    sorted_files = sorted(parsed_files, key=sort_key)

    # 为每个指标处理并保存CSV文件
    for metric in metrics:
        column_name = metric['column']
        output_file = metric['output']

        # 创建一个空的DataFrame用于存储当前指标的结果
        combined_df = pd.DataFrame()

        print(f"\n开始处理指标: {column_name}")

        # 遍历每个排序后的CSV文件
        for num, type_name, file in sorted_files:
            try:
                # 读取CSV文件
                df = pd.read_csv(file)

                # 检查是否包含当前指标列
                if column_name not in df.columns:
                    print(f"警告: 文件 {file} 中不包含 {column_name} 列，已跳过")
                    continue

                # 提取文件名（不包含路径和扩展名）作为新列名
                new_column_name = os.path.splitext(os.path.basename(file))[0]

                # 将提取的列添加到结果DataFrame中
                combined_df[new_column_name] = df[column_name]

                print(f"已处理: {file}")

            except Exception as e:
                print(f"处理文件 {file} 时出错: {str(e)}")

        # 保存合并后的结果到新的CSV文件
        if not combined_df.empty:
            combined_df.to_csv(output_file, index=False)
            print(f"指标 {column_name} 处理完成，结果已保存到 {output_file}")
        else:
            print(f"没有成功合并任何 {column_name} 数据")

if __name__ == "__main__":
    combine_csv_files()
if __name__ == "__main__":
    combine_csv_files()
