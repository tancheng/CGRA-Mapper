import pandas as pd
import matplotlib.pyplot as plt
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
        self.data_cache = {}  # Cache for loaded data
        self.figure_config = {
            'figsize': (10, 6),
            'xlabel': 'Data Row Index',
            'ylabel': 'Total_Execution_duration',
            'title': 'Total_Execution_duration Line Chart for Different Settings',
            'show_legend': True,
            'output_path': None  # If set, save figure instead of displaying
        }

    def load_data(self, kernel_case: str, csv_name: str) -> pd.DataFrame:
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
            required_columns = ['Total_Execution_duration', 'Overall_Case_Latency', 'CGRA_Utilization']

            # Check if required columns exist
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                raise ValueError(f"File is missing required columns: {', '.join(missing_columns)}")

            # Cache the data
            cache_key = f"{kernel_case}_{csv_name}"
            self.data_cache[cache_key] = df[required_columns]
            return self.data_cache[cache_key]

        except Exception as e:
            print(f"Failed to read file: {file_path}, Error: {str(e)}")
            return None

    def batch_load_data(self, kernel_cases: List[str]) -> Dict[str, pd.DataFrame]:
        """
        Batch load data from multiple CSV files

        Args:
            kernel_cases (List[str]): List of kernel case identifiers

        Returns:
            Dict[str, pd.DataFrame]: Mapping from cache keys to DataFrames
        """
        csv_names: List[str] = [
            'Baseline',
            'NoBosting',
            'BostingScalar',
            'BostingScalarFuse',
            'BostingScalarFuseVector'
        ]
        for kernel_case in kernel_cases:
            for csv_name in csv_names:
                self.load_data(kernel_case, csv_name)

        return self.data_cache

    def genFig9(self):
        """
        Generate Figure 9

        This method should be implemented to create the specific visualization
        """
        pass



def showTableI(csvPath, nameBaselineS):
    '''
    This is a func to read DFG nodes, edges, and RecMII from 6x6_*_baseline.csv and generate Table in csv.

    Parameters: path of csv, information of kernels in baseline

    Returns: NULL
    '''

    # read nodes, edges, and RecMII of 6x6_unroll1/unroll2_baseline.csv
    nameBaselineS.index(fileBaselineU1) # to check if the file name is correct
    nameBaselineS.index(fileBaselineU2) # to check if the file name is correct
    df = pd.read_csv(fileBaselineU1)
    yNodesU1 = df['DFG nodes'].tolist()[1:]
    yEdgesU1 = df['DFG edges'].tolist()[1:]
    yRecMIIU1 = df['recMII'].tolist()[1:]
    df = pd.read_csv(fileBaselineU2)
    yNodesU2 = df['DFG nodes'].tolist()[1:]
    yEdgesU2 = df['DFG edges'].tolist()[1:]
    yRecMIIU2 = df['recMII'].tolist()[1:]
    tmpList = [yNodesU1, yEdgesU1, yRecMIIU1, yNodesU2, yEdgesU2, yRecMIIU2]
    transList = [[row[i] for row in tmpList] for i in range(len(tmpList[0]))]   # transposition

    # generate a csv
    tableIDict = {'Kernel': "", 'Unroll1 Nodes': "", 'Unroll1 Edges': "", 'Unroll1 RecMII': "", 'Unroll2 Nodes': "", 'Unroll2 Edges': "", 'Unroll2 RecMII': ""}
    tableIDictColumn = len(tableIDict)
    df = pd.DataFrame(tableIDict, index=[0])
    dfBenchs = [[0] * (tableIDictColumn - 1) for _ in range(len(TEST_BENCHS))]  # a two-dim list with len(TEST_BENCHS) of Rows
    for i in range(len(TEST_BENCHS)):
        tmpList = [0]
        tmpList[0] = TEST_BENCHS[i]  # add kernel name in the head of list
        tmpList.extend(transList[i])    # add information of current kernel
        dfBenchs[i] = tmpList
    for i in range(len(TEST_BENCHS)):
        df.loc[len(df.index)] = dfBenchs[i]
    df.to_csv(csvPath)


def showFig9(figPath, nameBaselineS, namePertileS, nameIcedS):
    '''
    This is a func to read avg tile utilization from 6x6_*_*.csv and generate Parallel Bar Chart (Figure 9) in png.

    Parameters: path of figure, name of csv that stores Y-axis data

    Returns: NULL
    '''
    # read avg tile utilization of 6x6_unroll1/unroll2_baseline.csv
    nameBaselineS.index(fileBaselineU1) # to check if the file name is correct
    nameBaselineS.index(fileBaselineU2) # to check if the file name is correct
    df = pd.read_csv(fileBaselineU1)
    yBaselineU1 = df['avg tile utilization'].tolist()[1:]
    df = pd.read_csv(fileBaselineU2)
    yBaselineU2 = df['avg tile utilization'].tolist()[1:]
    # read avg tile utilization of 6x6_unroll1/unroll2_pertile.csv
    namePertileS.index(filePertileU1) # to check if the file name is correct
    namePertileS.index(filePertileU2) # to check if the file name is correct
    df = pd.read_csv(filePertileU1)
    yPertileU1 = df['avg tile utilization'].tolist()[1:]
    df = pd.read_csv(filePertileU2)
    yPertileU2 = df['avg tile utilization'].tolist()[1:]
    # read avg tile utilization of 6x6_unroll1/unroll2_iced.csv
    nameIcedS.index(fileIcedU1) # to check if the file name is correct
    nameIcedS.index(fileIcedU2) # to check if the file name is correct
    df = pd.read_csv(fileIcedU1)
    yIcedU1 = df['avg tile utilization'].tolist()[1:]
    df = pd.read_csv(fileIcedU2)
    yIcedU2 = df['avg tile utilization'].tolist()[1:]

    # draw a 6 bar chart
    plt.figure(figsize=(16, 5)) # the size of generated figure
    x = np.arange(len(TEST_BENCHS))  # X-axis
    xWidth = 0.1   # width of every bar
    plt.bar(x - xWidth*2.5, yBaselineU1, xWidth, label='Baseline Unroll1')
    plt.bar(x - xWidth*1.5, yPertileU1, xWidth, label='Per-tile DVFS + Power-gating Unroll1')
    plt.bar(x - xWidth*0.5, yIcedU1, xWidth, label='ICED Unroll1')
    plt.bar(x + xWidth*0.5, yBaselineU2, xWidth, label='Baseline Unroll2')
    plt.bar(x + xWidth*1.5, yPertileU2, xWidth, label='Per-tile DVFS + Power-gating Unroll2')
    plt.bar(x + xWidth*2.5, yIcedU2, xWidth, label='ICED Unroll2')
    plt.title('ExampleFig9')
    plt.ylabel('Avg utilization')
    plt.xticks(x, labels=TEST_BENCHS)
    plt.legend()
    plt.savefig(figPath)
