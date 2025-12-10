import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os
from typing import List, Dict, Any, Optional
import glob
import re

class SimulationDataAnalyzer:
    """Simulation data visualization analysis tool"""

    def __init__(self):
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
        self.figsize=(20, 8)

    def load_execution_data(self, kernel_case: str, csv_name: str, normalized_baseline: int) -> pd.DataFrame:
        """
        Load data from a single CSV file

        Args:
            kernel_case (str): Kernel case identifier
            csv_name (str): CSV file name identifier

        Returns:
            pd.DataFrame: DataFrame containing specified columns, or None if file doesn't exist
        """
        file_path = f'./result/simulation_{kernel_case}_{csv_name}.csv'

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
            cache_key = f"{kernel_case}_{csv_name}"
            self.execution_cache[cache_key] = df['Total_Execution_duration'] / normalized_baseline
            self.utilization_cache[cache_key] = df['CGRA_Utilization']
            return self.execution_cache[cache_key]

        except Exception as e:
            print(f"Failed to read file: {file_path}, Error: {str(e)}")
            return None

    def process_execution_data(self, kernel_cases: List[str]) -> Dict[str, pd.DataFrame]:
        """
        Batch load data from multiple CSV files

        Args:
            kernel_cases (List[str]): List of kernel case identifiers

        Returns:
            Dict[str, pd.DataFrame]: Mapping from cache keys to DataFrames
        """
        csv_names: List[str] = [
            'Baseline',
            'Neura-L0',
            'Neura-L1',
            'Neura-L2',
            'Neura'
        ]
        df = pd.read_csv("./result/simulation_1_Baseline.csv")
        normalized_baseline = df['Overall_Execution'].iloc[0] #case1 的 Baseline 的 overall execution time

        for kernel_case in kernel_cases:
            for csv_name in csv_names:
                self.load_execution_data(kernel_case, csv_name, normalized_baseline)

        return

    def load_throughput_data(self, kernel_case: str, csv_name: str) -> pd.DataFrame:
        """
        Load data from a single CSV file

        Args:
            kernel_case (str): Kernel case identifier
            csv_name (str): CSV file name identifier

        Returns:
            pd.DataFrame: DataFrame containing specified columns, or None if file doesn't exist
        """
        file_path = f'./result/simulation_{kernel_case}_{csv_name}.csv'

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
            cache_key = f"{kernel_case}_{csv_name}"
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

    def process_throughput_data(self, kernel_cases: List[str]) -> Dict[str, pd.DataFrame]:
        """
        Batch load data from multiple CSV files

        Args:
            kernel_cases (List[str]): List of kernel case identifiers

        Returns:
            Dict[str, pd.DataFrame]: Mapping from cache keys to DataFrames
        """
        csv_names: List[str] = [
            'Baseline',
            'Neura-L0',
            'Neura-L1',
            'Neura-L2',
            'Neura'
        ]
        df = pd.read_csv("./result/simulation_1_Baseline.csv")
        file_path = "./result/simulation_1_Baseline.csv"
        normalized_baseline = df['Overall_Execution'].iloc[0] #case1 的 Baseline 的 overall execution time

        for kernel_case in kernel_cases:
            for csv_name in csv_names:
                self.load_throughput_data(kernel_case, csv_name)

        return

    def load_scalability_data(self, kernel_case: str, csv_name: str, execution_baseline: int, latency_baseline: int) -> pd.DataFrame:
        """
        Load data from a single CSV file

        Args:
            kernel_case (str): Kernel case identifier
            csv_name (str): CSV file name identifier

        Returns:
            pd.DataFrame: DataFrame containing specified columns, or None if file doesn't exist
        """
        file_path = f'./result/simulation_{kernel_case}_{csv_name}.csv'
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
            cache_key = f"{kernel_case}_{csv_name}"
            self.scalability_cache[cache_key] = df['Total_Execution_duration'] / execution_baseline
            self.latency_cache[cache_key] = df['Overall_Case_Latency'] / latency_baseline
            self.utilization_cache[cache_key] = df['CGRA_Utilization']
            return self.scalability_cache[cache_key]

        except Exception as e:
            print(f"Failed to read file: {file_path}, Error: {str(e)}")
            return None

    def process_scalability_data(self, kernel_cases: List[str]) -> Dict[str, pd.DataFrame]:
        """
        Batch load data from multiple CSV files

        Args:
            kernel_cases (List[str]): List of kernel case identifiers

        Returns:
            Dict[str, pd.DataFrame]: Mapping from cache keys to DataFrames
        """
        csv_names: List[str] = [
            'Baseline',
            'Neura-L0',
            'Neura-L1',
            'Neura-L2',
            'Neura'
        ]
        df = pd.read_csv("./result/simulation_2x2_6_Baseline.csv")
        normalized_baseline = df['Overall_Execution'].iloc[0]
        latency_baseline = df['Overall_Case_Latency'].iloc[0]
        for kernel_case in kernel_cases:
            for csv_name in csv_names:
                self.load_scalability_data(kernel_case, csv_name, normalized_baseline, latency_baseline)

        return




    def update_config(self) -> None:
        pass

    def genFig9(self, fig_path: str):
        """Create correct combined chart - one bar and one line point per X position"""
        print(f"Generating fig f{fig_path}")
        # Group structure
        groups: list = [
            'Baseline',
            'Neura-L0',
            'Neura-L1',
            'Neura-L2',
            'Neura'
        ]
        cases = ['1', '2', '3', '4', '5', '6']
        self.process_execution_data(cases)

        # Correct data structure - one value per X position
        bar_data = []  # Bar chart data
        line_data = [] # Line chart data
        x_labels = []  # X-axis labels

        # Collect data
        for case in cases:
            for group in groups:
                cache_key = f"{case}_{group}"  # Adjust based on your actual naming convention
                execution_series = self.execution_cache.get(cache_key)
                utilization_series = self.utilization_cache.get(cache_key)

                # Bar chart data - Resource utilization
                if execution_series is not None:
                    bar_value = execution_series.sum()
                    bar_data.append(float(bar_value) * 100)
                else:
                    bar_data.append(0)

                # Line chart data - Execution duration or other metrics
                if utilization_series is not None:
                    line_value = utilization_series.iloc[0]
                    line_data.append(float(line_value))
                else:
                    line_data.append(0)

                x_labels.append(f"{group}")

        # Create chart
        fig, ax1 = plt.subplots(figsize=(20, 8))

        x_positions = np.arange(len(bar_data))
        bar_width = 0.6

        # Primary Y-axis - Bar chart
        bars = ax1.bar(x_positions, bar_data, bar_width,
                    color='skyblue', alpha=0.8,
                    label='Total_Execution_duration')

        ax1.set_ylabel('Execution time', fontsize=12, color='black')
        ax1.tick_params(axis='y', labelcolor='black')
        ax1.set_ylim(0, 100)

        # Display values on bars
        # for bar, value in zip(bars, bar_data):
        #     height = bar.get_height()
        #     ax1.text(bar.get_x() + bar.get_width()/2., height + 1,
        #             f'{value:.1f}%', ha='center', va='bottom', fontsize=9)

        # Secondary Y-axis - Line chart
        ax2 = ax1.twinx()

        # Calculate number of complete cases
        num_complete_cases = len(x_positions) // len(groups)

        # Insert NaN every 5 points
        x_with_gaps = []
        y_with_gaps = []

        for case_idx in range(num_complete_cases):
            # Start and end indices for this case
            start_idx = case_idx * len(groups)
            end_idx = start_idx + len(groups)

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

        ax2.set_ylabel('Utilization (%)', fontsize=12, color='black')
        ax2.tick_params(axis='y', labelcolor='black')

        # Display values on line points
        for i, (x, y) in enumerate(zip(x_positions, line_data)):
            ax2.text(x, y + max(line_data)*0.02, f'{y:.1f}',
                    ha='center', va='bottom', fontsize=9)

        # Set X-axis labels and grouping
        ax1.set_xticks(x_positions)
        ax1.set_xticklabels(x_labels, rotation=90)

        # Add group labels
        group_positions = [3, 8, 13, 17, 22, 27]  # Middle position of each group
        for case, pos in zip(cases, group_positions):
            ax1.text(pos, -0.15, case, transform=ax1.get_xaxis_transform(),
                    ha='center', va='top', fontsize=13, fontweight='bold',
                    bbox=dict(boxstyle="round,pad=0.3", facecolor='lightgray', alpha=0.8))


        # Legends
        ax1.legend(loc='upper left')
        ax2.legend(loc='upper right')

        ax1.grid(True, linestyle='--', alpha=0.3, axis='y')
        plt.title('ExampleFig9')
        plt.tight_layout()
        # plt.legend()
        plt.savefig(fig_path)

    def genFig10(self, fig_path: str):
        """
        Generate Figure 10: Normalized throughput speedup
        """
        print(f"Generating fig f{fig_path}")
        groups: list = [
            'Baseline',
            'Neura-L0',
            'Neura-L1',
            'Neura-L2',
            'Neura'
        ]
        bar_colors = [
            '#7F7F7F',  # Gray
            '#EDEDED',  # White/Light gray
            '#FFF2CC',  # Light yellow
            '#FFD966',  # Orange-yellow
            '#FFC000'   # Orange
        ]
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

            for group in groups:
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
        fig, ax1 = plt.subplots(figsize=(10, 8))

        x_positions = np.arange(len(bar_data))
        bar_width = 0.6

        bars = ax1.bar(x_positions, bar_data, bar_width,
                    color=bar_colors[:len(bar_data)],
                    alpha=0.8)

        ax1.set_ylabel('Normalized Throughput Speedup', fontsize=12, color='black')
        ax1.tick_params(axis='y', labelcolor='black')
        ax1.set_ylim(0, 4)

        # Display values on bars
        # for bar, value in zip(bars, bar_data):
        #     height = bar.get_height()
        #     ax1.text(bar.get_x() + bar.get_width()/2., height + 1,
        #             f'{value}', ha='center', va='bottom', fontsize=9)

        # Set X-axis labels and grouping
        ax1.set_xticks(x_positions)
        ax1.set_xticklabels(x_labels, rotation=90)

        # Add group labels
        group_positions = [3, 8, 13, 17, 22, 27]  # Middle position of each group
        for case, pos in zip(cases, group_positions):
            ax1.text(pos, -0.15, case, transform=ax1.get_xaxis_transform(),
                    ha='center', va='top', fontsize=13, fontweight='bold',
                    bbox=dict(boxstyle="round,pad=0.3", facecolor='lightgray', alpha=0.8))

        # Legends
        ax1.legend(loc='upper left')

        ax1.grid(True, linestyle='--', alpha=0.3, axis='y')
        plt.title('ExampleFig10')
        plt.tight_layout()
        # plt.legend()
        plt.savefig(fig_path)

    def genFig11(self, fig_path: str):
        """
        Generate Figure 11: Scalability -- Normalized execution time and improved utilization
        """
        # Group structure
        groups: list = [
            'Baseline',
            'Neura-L0',
            'Neura-L1',
            'Neura-L2',
            'Neura'
        ]
        cases = ['2x2_6', '3x3_6', '4x4_6', '5x5_6']
        self.process_scalability_data(cases)

        # Correct data structure - one value per X position
        bar_data = []  # Bar chart data
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
            for group in groups:
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
                # Bar chart data - Resource utilization
                bar_data.append(sum(throughput_speedup))

                # Line chart data - Execution duration or other metrics
                if utilization_series is not None:
                    line_value = utilization_series.iloc[0]
                    line_data.append(float(line_value))
                else:
                    line_data.append(0)

                x_labels.append(f"{group}")
        # sum_throughput = throughput_speedup.sum()
        # Create chart
        fig, ax1 = plt.subplots(figsize=(20, 12))

        x_positions = np.arange(len(bar_data))
        bar_width = 0.6

        # Primary Y-axis - Bar chart
        bars = ax1.bar(x_positions, bar_data, bar_width,
                    color='skyblue', alpha=0.8,
                    label='Total_Execution_duration')

        ax1.set_ylabel('Normalized Throughput Speedup', fontsize=12, color='black')
        ax1.tick_params(axis='y', labelcolor='black')
        ax1.set_ylim(0, 26)

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

        ax2.set_ylabel('Utilization (%)', fontsize=12, color='black')
        ax2.tick_params(axis='y', labelcolor='black')
        ax2.set_ylim(0, 1.2)
        ax2.set_yticks(np.arange(0, 1.3, 0.1))

        # Display values on line points
        for i, (x, y) in enumerate(zip(x_positions, line_data)):
            ax2.text(x, y + max(line_data)*0.02, f'{y:.1f}',
                    ha='center', va='bottom', fontsize=9)

        # Set X-axis labels and grouping
        ax1.set_xticks(x_positions)
        ax1.set_xticklabels(x_labels, rotation=90)

        # Add group labels
        group_positions = [3, 8, 13, 17, 22, 27]  # Middle position of each group
        for case, pos in zip(cases, group_positions):
            ax1.text(pos, -0.15, case, transform=ax1.get_xaxis_transform(),
                    ha='center', va='top', fontsize=13, fontweight='bold',
                    bbox=dict(boxstyle="round,pad=0.3", facecolor='lightgray', alpha=0.8))
        # Legends
        ax1.legend(loc='upper left')
        ax2.legend(loc='upper right')

        ax1.grid(True, linestyle='--', alpha=0.3, axis='y')
        plt.title('ExampleFig9')
        plt.tight_layout()
        # plt.legend()
        plt.savefig(fig_path)
        print(f"Generated fig f{fig_path}")

if __name__ == '__main__':
    genFigs = SimulationDataAnalyzer()
    genFigs.genFig9("./fig/Fig9.png")
    # genFigs.genFig10("./fig/Fig10.png")
    # genFigs.genFig11("./fig/Fig11.png")