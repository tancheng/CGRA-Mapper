# ----------------------------------------------------------------------------
#   Filename: main.py                                                       /
#   Description: load multi-task and schedule them on multi-CGRA            /
# ----------------------------------------------------------------------------

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os
from typing import List, Dict

# ----------------------------------------------------------------------------
#   class defination                                                         /
# ----------------------------------------------------------------------------

class SimulationDataAnalyzer:
    """Simulation data visualization analysis tool"""

    def __init__(self, kernel_data):
        """
        Initialize the analyzer

        Attributes:
            data_cache (dict): Cache for loaded data
            figure_config (dict): Default configuration for figures
        """
        self.execution_cache = {}  # Cache for loaded data
        self.utilization_cache = {}
        self.throughput_cache = {}
        self.number_cache = {}
        self.waiting_cache = {}
        self.scalability_cache = {}
        self.latency_cache = {}
        self.KERNEL_NAMES = list(kernel_data.keys())
        self.NEURA_CONFIGS = ['Baseline', 'Neura-L0', 'Neura-L1', 'Neura-L2', 'Neura']
        self.KERNEL_COLORS = ['#A4A3A4','#B0C4E6','#8DA9DC','#FEEDB9','#002060',
                            '#F3B082','#F7CAAB','#C7FAA8','#FFD865']
        self.NEURA_COLORS = ['#7F7F7F','#EDEDED','#FFF2CC','#FFD966','#FFC000']

    def load_execution_data(self, task_case: str, csv_name: str, normalized_baseline: int):
        """
        Load data from a single CSV file

        Args:
            task_case (str): Kernel case identifier
            csv_name (str): CSV file name identifier

        Returns:
            pd.DataFrame: DataFrame containing specified columns, or None if file doesn't exist
        """
        file_path = f'./result/simulation_{task_case}_{csv_name}.csv'

        if not os.path.exists(file_path):
            print(f"File does not exist: {file_path}")
            return None

        # Read specified columns from the data
        try:
            df = pd.read_csv(file_path)
            required_columns = ['Total_Execution_duration', 'Overall_Execution', 'CGRA_Utilization']

            # Check if required columns exist
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                raise ValueError(f"File is missing required columns: {', '.join(missing_columns)}")

            # Cache the data
            cache_key = f"{task_case}_{csv_name}"
            self.execution_cache[cache_key] = df['Total_Execution_duration'] / normalized_baseline
            self.utilization_cache[cache_key] = df['CGRA_Utilization']
            return self.execution_cache[cache_key]

        except Exception as e:
            print(f"Failed to read file: {file_path}, Error: {str(e)}")
            return None

    def process_execution_data(self, task_cases: List[str]):
        """
        Batch load data from multiple CSV files

        Args:
            task_cases (List[str]): List of kernel case identifiers

        Returns:
            Dict[str, pd.DataFrame]: Mapping from cache keys to DataFrames
        """
        df = pd.read_csv("./result/simulation_1_Baseline.csv")
        normalized_baseline = df['Overall_Execution'].iloc[0] #case1 的 Baseline 的 overall execution time

        for task_case in task_cases:
            for csv_name in self.NEURA_CONFIGS:
                self.load_execution_data(task_case, csv_name, normalized_baseline)

        return

    def load_throughput_data(self, task_case: str, csv_name: str):
        """
        Load data from a single CSV file

        Args:
            task_case (str): Kernel case identifier
            csv_name (str): CSV file name identifier

        Returns:
            pd.DataFrame: DataFrame containing specified columns, or None if file doesn't exist
        """
        file_path = f'./result/simulation_{task_case}_{csv_name}.csv'

        if not os.path.exists(file_path):
            print(f"File does not exist: {file_path}")
            return None

        # Read specified columns from the data
        try:
            df = pd.read_csv(file_path)
            required_columns = ['Total_Execution_duration', 'waiting_time_nolap', 'Average_Execution_duration']

            # Check if required columns exist
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                raise ValueError(f"File is missing required columns: {', '.join(missing_columns)}")

            # Cache the data
            cache_key = f"{task_case}_{csv_name}"
            self.execution_cache[cache_key] = df['Total_Execution_duration']
            self.number_cache[cache_key] = np.where(
                (df['Average_Execution_duration'] == 0),
                0,
                df['Total_Execution_duration'] / df['Average_Execution_duration']
            )
            self.waiting_cache[cache_key] = df['waiting_time_nolap']

            return self.execution_cache[cache_key]

        except Exception as e:
            print(f"Failed to read file: {file_path}, Error: {str(e)}")
            return None

    def process_throughput_data(self, task_cases: List[str]):
        """
        Batch load data from multiple CSV files

        Args:
            task_cases (List[str]): List of kernel case identifiers

        Returns:
            Dict[str, pd.DataFrame]: Mapping from cache keys to DataFrames
        """
        df = pd.read_csv("./result/simulation_1_Baseline.csv")
        file_path = "./result/simulation_1_Baseline.csv"
        normalized_baseline = df['Overall_Execution'].iloc[0] #case1 的 Baseline 的 overall execution time

        for task_case in task_cases:
            for csv_name in self.NEURA_CONFIGS:
                self.load_throughput_data(task_case, csv_name)

        return

    def load_scalability_data(self, task_case: str, csv_name: str, execution_baseline: int, latency_baseline: int):
        """
        Load data from a single CSV file

        Args:
            task_case (str): Kernel case identifier
            csv_name (str): CSV file name identifier

        Returns:
            pd.DataFrame: DataFrame containing specified columns, or None if file doesn't exist
        """
        file_path = f'./result/simulation_{task_case}_{csv_name}.csv'
        print(file_path)
        if not os.path.exists(file_path):
            print(f"File does not exist: {file_path}")
            return None

        # Read specified columns from the data
        try:
            df = pd.read_csv(file_path)
            required_columns = ['Total_Execution_duration', 'Overall_Execution', 'CGRA_Utilization', 'Overall_Case_Latency']

            # Check if required columns exist
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                raise ValueError(f"File is missing required columns: {', '.join(missing_columns)}")

            # Cache the data
            cache_key = f"{task_case}_{csv_name}"
            self.scalability_cache[cache_key] = df['Total_Execution_duration'] / execution_baseline
            self.latency_cache[cache_key] = df['Overall_Case_Latency'] / latency_baseline
            self.utilization_cache[cache_key] = df['CGRA_Utilization']
            return self.scalability_cache[cache_key]

        except Exception as e:
            print(f"Failed to read file: {file_path}, Error: {str(e)}")
            return None

    def process_scalability_data(self, task_cases: List[str]):
        """
        Batch load data from multiple CSV files

        Args:
            task_cases (List[str]): List of kernel case identifiers

        Returns:
            Dict[str, pd.DataFrame]: Mapping from cache keys to DataFrames
        """
        df = pd.read_csv("./result/simulation_2x2_6_Baseline.csv")
        normalized_baseline = df['Overall_Execution'].iloc[0]
        latency_baseline = df['Overall_Case_Latency'].iloc[0]
        for task_case in task_cases:
            for csv_name in self.NEURA_CONFIGS:
                self.load_scalability_data(task_case, csv_name, normalized_baseline, latency_baseline)

        return

    def genFig9(self, fig_path: str):
        """
        Generate Figure 9: Normalized execution time and improved utilization
        """
        cases = ['1', '2', '3', '4', '5', '6']
        self.process_execution_data(cases)

        # Correct data structure - one value per X position
        bar_data = {kernel: [] for kernel in self.KERNEL_NAMES}  # Bar chart data
        line_data = [] # Line chart data
        x_labels = []  # X-axis labels

        # Collect data
        for case in cases:
            for group in self.NEURA_CONFIGS:
                cache_key = f"{case}_{group}"  # Adjust based on your actual naming convention
                execution_series = self.execution_cache.get(cache_key)
                utilization_series = self.utilization_cache.get(cache_key)

                # Bar chart data - Resource utilization
                if execution_series is not None:
                    if hasattr(execution_series, 'to_dict'):
                        exec_dict = execution_series.to_dict()
                    else:
                        exec_dict = dict(execution_series)
                    for i, kernel in enumerate(self.KERNEL_NAMES):
                        kernel_value = float(exec_dict[i]) * 100
                        bar_data[kernel].append(kernel_value)
                else:
                    for kernel in self.KERNEL_NAMES:
                        bar_data[kernel].append(0)

                # Line chart data - Execution duration or other metrics
                if utilization_series is not None:
                    line_value = utilization_series.iloc[0]
                    line_data.append(float(line_value) * 100)
                else:
                    line_data.append(0)

                x_labels.append(f"{group}")

        # Create chart
        fig, ax1 = plt.subplots(figsize=(20, 8))
        plt.style.use({
            'font.size': 20,
            'axes.labelsize': 18,
            'axes.titlesize': 18,
            'xtick.labelsize': 18,
            'ytick.labelsize': 18
        })

        total_bars = len(cases) * len(self.NEURA_CONFIGS)
        x_positions = np.arange(total_bars)
        bar_width = 0.6
        # Primary Y-axis - Bar chart
        color_dict = {kernel: color for kernel, color in zip(self.KERNEL_NAMES, self.KERNEL_COLORS)}
        bottom = np.zeros(total_bars)
        bars_by_kernel = {}
        for kernel in self.KERNEL_NAMES:
            data = bar_data[kernel]
            bars = ax1.bar(x_positions, data, bar_width, bottom=bottom,
                        color=color_dict[kernel], alpha=0.8,
                        edgecolor='black', linewidth=0.5, label=kernel)
            bars_by_kernel[kernel] = bars
            bottom += np.array(data)


        # Add black dashed separator lines every group
        for i in range(4, len(x_positions)-1, 5):
            line_pos = i + 0.5
            ax1.axvline(x=line_pos,
                    color='black',
                    linestyle='--',
                    linewidth=0.8,
                    alpha=0.8)

        # Display values on Neura
        arrays = [np.array(heights) for heights in bar_data.values()]
        total_heights = np.sum(arrays, axis=0)
        for i, (x, y) in enumerate(zip(x_positions, total_heights)):
            if (i + 1) % 5 == 0:
                ax1.text(x, y + max(total_heights)*0.02, f'{y:.1f}',
                        ha='center', va='bottom', fontsize=10)

        ax1.set_ylabel('Normalized execution time (%)', fontsize=20, color='black')
        ax1.tick_params(axis='y', labelcolor='black', labelsize=18)
        ax1.set_ylim(0, 120)
        ax1.legend(loc='upper left', bbox_to_anchor=(1.05, 1), borderaxespad=0.,
                fontsize=12, title="Kernels", title_fontsize=13)

        # Secondary Y-axis - Line chart
        ax2 = ax1.twinx()

        # Calculate number of complete cases
        num_complete_cases = len(x_positions) // len(self.NEURA_CONFIGS)

        # Insert NaN every 5 points
        x_with_gaps = []
        y_with_gaps = []

        for case_idx in range(num_complete_cases):
            # Start and end indices for this case
            start_idx = case_idx * len(self.NEURA_CONFIGS)
            end_idx = start_idx + len(self.NEURA_CONFIGS)

            # Add 5 points for this case
            x_with_gaps.extend(x_positions[start_idx:end_idx])
            y_with_gaps.extend(line_data[start_idx:end_idx])

            # Add NaN after each case (except the last complete case)
            if case_idx < num_complete_cases - 1:
                x_with_gaps.append(np.nan)
                y_with_gaps.append(np.nan)


        # Convert to numpy arrays
        x_with_gaps = np.array(x_with_gaps)
        y_with_gaps = np.array(y_with_gaps)

        # Plot line with gaps between cases
        line = ax2.plot(x_with_gaps, y_with_gaps,
                        marker='o', markersize=8, linewidth=2.5,
                        color='blue', linestyle='--',
                        markerfacecolor='white', markeredgewidth=2,
                        label='Utilization')

        ax2.set_ylabel('Resource Utilization (%)', fontsize=20, color='black')
        ax2.tick_params(axis='y', labelcolor='black', labelsize=18)

        # Display values on line points
        for i, (x, y) in enumerate(zip(x_positions, line_data)):
            ax2.text(x, y + max(line_data)*0.02, f'{y:.1f}',
                    ha='center', va='bottom', fontsize=10)

        # Set X-axis labels and grouping
        ax1.set_xticks(x_positions)
        ax1.set_xticklabels(x_labels, rotation=90)
        ax1.tick_params(axis='x', labelsize=18)

        # Add group labels
        group_positions = [3, 8, 13, 17, 22, 27]  # Middle position of each group
        for case, pos in zip(cases, group_positions):
            ax1.text(pos, -0.15, 'case ' + case, transform=ax1.get_xaxis_transform(),
                    ha='center', va='top', fontsize=20, fontweight='bold',
                    bbox=dict(boxstyle="round,pad=0.3", facecolor='lightgray', alpha=0.8))

        ax1.grid(True, linestyle='--', alpha=0.3, axis='y')
        plt.title('ExampleFig9')
        plt.tight_layout()
        plt.savefig(fig_path)
        print(f"Generated fig f{fig_path}")

    def genFig10(self, fig_path: str):
        """
        Generate Figure 10: Normalized throughput speedup
        """
        cases = ['1', '2', '3', '4', '5', '6']
        self.process_throughput_data(cases)

        # Correct data structure - one value per X position
        bar_data = []  # Bar chart data
        x_labels = []  # X-axis labels
        # Collect data
        for case in cases:
            cache_key = f"{case}_Baseline"
            execution_series = self.execution_cache.get(cache_key)
            number_series = self.number_cache.get(cache_key)
            waiting_series = self.waiting_cache.get(cache_key)
            hw_waiting = waiting_series.iloc[0] / int(number_series.sum())
            avg_execution = execution_series.sum() / int(number_series.sum())
            hw_waiting_ratio = hw_waiting / (hw_waiting + avg_execution)
            avg_execution_ratio = avg_execution / (hw_waiting + avg_execution)
            hw_waiting_baseline = hw_waiting
            avg_execution_baseline = avg_execution
            throughput_baseline = (hw_waiting_ratio + avg_execution_ratio)

            for group in self.NEURA_CONFIGS:
                cache_key = f"{case}_{group}"  # Adjust based on your actual naming convention
                execution_series = self.execution_cache.get(cache_key)
                number_series = self.number_cache.get(cache_key)
                waiting_series = self.waiting_cache.get(cache_key)
                if (execution_series is None or number_series is None or
                waiting_series is None):
                    continue
                hw_waiting = waiting_series.iloc[0] / int(number_series.sum())
                avg_execution = execution_series.sum() / int(number_series.sum())
                hw_waiting_ratio = hw_waiting / (hw_waiting_baseline + avg_execution_baseline)
                avg_execution_ratio = avg_execution / (hw_waiting_baseline + avg_execution_baseline)
                bar_data.append(throughput_baseline / (hw_waiting_ratio + avg_execution_ratio))

                x_labels.append(f"{group}")
        # sum_throughput = throughput_speedup.sum()
        # Create chart
        fig, ax1 = plt.subplots(figsize=(20, 8))
        plt.style.use({
            'font.size': 20,
            'axes.labelsize': 18,
            'axes.titlesize': 18,
            'xtick.labelsize': 18,
            'ytick.labelsize': 18
        })

        x_positions = np.arange(len(bar_data))
        bar_width = 0.6

        bars = ax1.bar(x_positions, bar_data, bar_width,
               color=self.NEURA_COLORS[:len(bar_data)],
               alpha=0.8,
               edgecolor='black',
               linewidth=0.5)

        # Add black dashed separator lines every group
        for i in range(4, len(bar_data)-1, 5):
            line_pos = i + 0.5
            ax1.axvline(x=line_pos,
                    color='black',
                    linestyle='--',
                    linewidth=0.8,
                    alpha=0.8)

        for i, (x, y) in enumerate(zip(x_positions, bar_data)):
            if (i + 1) % 5 == 0:
                ax1.text(x, y + max(bar_data)*0.02, f'{y:.1f}',
                        ha='center', va='bottom', fontsize=10)

        ax1.set_ylabel('Normalized Throughput Speedup', fontsize=20, color='black')
        ax1.tick_params(axis='y', labelcolor='black')
        ax1.set_ylim(0, 4)


        # Set X-axis labels and grouping
        ax1.set_xticks(x_positions)
        ax1.set_xticklabels(x_labels, rotation=90)

        # Add group labels
        group_positions = [3, 8, 13, 17, 22, 27]  # Middle position of each group
        for case, pos in zip(cases, group_positions):
            ax1.text(pos, -0.15, 'case ' + case, transform=ax1.get_xaxis_transform(),
                    ha='center', va='top', fontsize=20, fontweight='bold',
                    bbox=dict(boxstyle="round,pad=0.3", facecolor='lightgray', alpha=0.8))

        # Legends
        ax1.legend(loc='upper left')

        ax1.grid(True, linestyle='--', alpha=0.3, axis='y')
        plt.title('ExampleFig10')
        plt.tight_layout()
        # plt.legend()
        plt.savefig(fig_path)
        print(f"Generated fig {fig_path}")

    def genFig11(self, fig_path: str):
        """
        Generate Figure 11: Scalability -- Normalized execution time and improved utilization
        """
        cases = ['2x2_6', '3x3_6', '4x4_6', '5x5_6']
        self.process_scalability_data(cases)

        # Correct data structure - one value per X position
        bar_data = {kernel: [] for kernel in self.KERNEL_NAMES}  # Bar chart data
        line_data = [] # Line chart data
        x_labels = []  # X-axis labels
        # Collect data
        cache_key = "2x2_6_Baseline"
        scalability_series = self.scalability_cache.get(cache_key)
        latency_series = self.latency_cache.get(cache_key)
        throughput_speedup = [0] * len(scalability_series)
        for i in range(len(scalability_series)):
            throughput_speedup[i] = (1 / (scalability_series[i] * latency_series[i] * 100))
        throughput_baseline = sum(throughput_speedup)
        for case in cases:
            for group in self.NEURA_CONFIGS:
                cache_key = f"{case}_{group}"  # Adjust based on your actual naming convention
                scalability_series = self.scalability_cache.get(cache_key)
                utilization_series = self.utilization_cache.get(cache_key)
                latency_series = self.latency_cache.get(cache_key)
                if (scalability_series is None or latency_series is None or
                utilization_series is None):
                    continue
                for i in range(len(scalability_series)):
                    if scalability_series[i] * latency_series[i] == 0:
                        tmp = 0
                    else:
                        tmp = (1 / (scalability_series[i] * latency_series[i] * 100))
                    throughput_speedup[i] = tmp / throughput_baseline
                # Bar chart data
                for i, kernel in enumerate(self.KERNEL_NAMES):
                    bar_data[kernel].append(throughput_speedup[i])

                # Line chart data
                if utilization_series is not None:
                    line_value = utilization_series.iloc[0]
                    line_data.append(float(line_value) * 100)
                else:
                    line_data.append(0)

                x_labels.append(f"{group}")

        # Create chart
        fig, ax1 = plt.subplots(figsize=(20, 8))
        plt.style.use({
            'font.size': 20,
            'axes.labelsize': 18,
            'axes.titlesize': 18,
            'xtick.labelsize': 18,
            'ytick.labelsize': 18
        })


        total_bars = (len(cases) * (len(self.NEURA_CONFIGS) - 1)) + 1
        x_positions = np.arange(total_bars)
        bar_width = 0.6
        # Primary Y-axis - Bar chart
        color_dict = {kernel: color for kernel, color in zip(self.KERNEL_NAMES, self.KERNEL_COLORS)}
        bottom = np.zeros(total_bars)
        bars_by_kernel = {}
        for kernel in self.KERNEL_NAMES:
            data = bar_data[kernel]
            bars = ax1.bar(x_positions, data, bar_width, bottom=bottom,
                        color=color_dict[kernel], alpha=0.8,
                        edgecolor='black', linewidth=0.5, label=kernel)
            bars_by_kernel[kernel] = bars
            bottom += np.array(data)

        # Add black dashed separator lines every group
        group_pattern = [5, 4, 4, 4]
        current_position = 0
        line_positions = []
        for group_size in group_pattern:
            current_position += group_size
            if current_position < len(x_positions):
                line_positions.append(current_position - 0.5)
        for pos in line_positions:
            ax1.axvline(x=pos,
                        color='black',
                        linestyle='--',
                        linewidth=0.8,
                        alpha=0.8)

        # Display values on Neura
        display_indices = []
        for i in range(len(x_positions)):
            if i >= 4 and (i - 4) % 4 == 0:
                display_indices.append(i)
        arrays = [np.array(heights) for heights in bar_data.values()]
        total_heights = np.sum(arrays, axis=0)
        for i, (x, y) in enumerate(zip(x_positions, total_heights)):
            if i in display_indices:
                ax1.text(x, y + max(total_heights)*0.02, f'{y:.1f}',
                        ha='center', va='bottom', fontsize=10)

        ax1.set_ylabel('Normalized Throughput Speedup', fontsize=20, color='black')
        ax1.tick_params(axis='y', labelcolor='black')
        ax1.set_ylim(0, 26)
        ax1.legend(loc='upper left', bbox_to_anchor=(1.05, 1), borderaxespad=0.,
                fontsize=12, title="Kernels", title_fontsize=13)

        # Secondary Y-axis - Line chart
        ax2 = ax1.twinx()

        # Define break pattern: first group 5 points, then 4 points for others
        break_pattern = [5]  # First case: 5 points
        remaining_cases = (len(x_positions) - 5) // 4  # Calculate how many 4-point cases
        break_pattern.extend([4] * remaining_cases)  # Add 4 for each remaining case

        # Insert NaN based on the break pattern
        x_with_gaps = []
        y_with_gaps = []

        current_idx = 0
        for i, num_points in enumerate(break_pattern):
            # Add points for this case
            end_idx = current_idx + num_points
            x_with_gaps.extend(x_positions[current_idx:end_idx])
            y_with_gaps.extend(line_data[current_idx:end_idx])

            # Add NaN after this case (except the last one)
            if i < len(break_pattern) - 1:
                x_with_gaps.append(np.nan)
                y_with_gaps.append(np.nan)

            current_idx = end_idx

        x_with_gaps = np.array(x_with_gaps)
        y_with_gaps = np.array(y_with_gaps)

        # Plot line with gaps between cases
        line = ax2.plot(x_with_gaps, y_with_gaps,
                        marker='o', markersize=8, linewidth=2.5,
                        color='blue', linestyle='--',
                        markerfacecolor='white', markeredgewidth=2,
                        label='Utilization')

        ax2.set_ylabel('Resource Utilization (%)', fontsize=20, color='black')
        ax2.tick_params(axis='y', labelcolor='black')
        ax2.set_ylim(0, 100)
        ax2.set_yticks(np.arange(0, 120, 30))

        # Display values on line points
        for i, (x, y) in enumerate(zip(x_positions, line_data)):
            ax2.text(x, y + max(line_data)*0.02, f'{y:.1f}',
                    ha='center', va='bottom', fontsize=10)

        # Set X-axis labels and grouping
        ax1.set_xticks(x_positions)
        ax1.set_xticklabels(x_labels, rotation=90)

        # Add group labels
        group_positions = [3, 7, 11, 15]  # Middle position of each group
        for case, pos in zip(cases, group_positions):
            ax1.text(pos, -0.15, (case.split('_'))[0] + 'Neura', transform=ax1.get_xaxis_transform(),
                    ha='center', va='top', fontsize=20, fontweight='bold',
                    bbox=dict(boxstyle="round,pad=0.3", facecolor='lightgray', alpha=0.8))

        ax1.grid(True, linestyle='--', alpha=0.3, axis='y')
        plt.title('ExampleFig11')
        plt.tight_layout()
        # plt.legend()
        plt.savefig(fig_path)
        print(f"Generated fig {fig_path}")

if __name__ == '__main__':
    KERNEL_DATA = {
    "fir.cpp": (7, 2048, 4096),
    "latnrm.c": (8, 1280, 2560),
    "fft.c": (2, 112640, 450560),
    "dtw.cpp": (4, 16384, 49152),
    "spmv.c": (3, 65536, 262144),
    "conv.c": (1, 655360, 1310720),
    "mvt.c": (5, 16384, 49152),
    "gemm.c": (0, 2097152, 8388608),
    "relu+histogram.c": (6, 262144, 2097152)
    }
    genFigs = SimulationDataAnalyzer(kernel_data=KERNEL_DATA)
    genFigs.genFig9("./fig/Fig9Test.png")
    #genFigs.genFig10("./fig/Fig10.png")
    genFigs.genFig11("./fig/Fig11Test.png")