# ----------------------------------------------------------------------------
#   Filename: SORAdemo.py                                                   /
#   Description: simulate multi-kernel running on multi-CGRA                /
#   Author: Miaomiao Jiang, start from 2025-02-24                           /
# ----------------------------------------------------------------------------

import heapq
import subprocess
import json
import eventlet    # for time out
import pandas as pd
import math
from types import SimpleNamespace
import argparse

# ----------------------------------------------------------------------------
#   global variables                                                        /
# ----------------------------------------------------------------------------

TEST_BENCHS = ["fir.cpp", "latnrm.c", "fft.c", "dtw.cpp", "spmv.c", "conv.c", "relu.c", "histogram.cpp", "mvt.c", "gemm.c", "spmv+conv.c", "relu+histogram.c"]
TEST_BENCHS_NUM = len(TEST_BENCHS)
DICT_CSV = {'kernels': "", 'DFG nodes': "", 'DFG edges': "", 'recMII': "", 'mappingII': "", 'expandableII': "", 'utilization': ""}  # column names of generated CSV
DICT_COLUMN = len(DICT_CSV)
JSON_NAME = "./param.json"   # name of generated json file
TIME_OUT_SET = 180
DO_MAPPING = True
KERNEL_DIRECTORY = "./kernels"
VECTOR_LANE = 2


def str_to_bool(value):
    if isinstance(value, bool):
        return value
    if str(value).lower() in ('yes', 'true', 't', 'y', '1'):
        return True
    elif str(value).lower() in ('no', 'false', 'f', 'n', '0'):
        return False
    raise argparse.ArgumentTypeError('Invalid boolean value (accepted: 0/1, true/false, yes/no)')


def load_configuration():
    """Load and merge configurations from multiple sources with priority:
    1. Command line arguments (highest priority)
    2. JSON config file
    3. Default values (lowest priority)
    """
    global JSON_NAME, KERNEL_DIRECTORY, VECTOR_LANE, DO_MAPPING, TIME_OUT_SET

    # Default configuration values
    defaults = {
        "JSON_NAME": JSON_NAME,
        "KERNEL_DIRECTORY": KERNEL_DIRECTORY,
        "VECTOR_LANE": VECTOR_LANE,
        "DO_MAPPING": DO_MAPPING,
        "TIME_OUT_SET": TIME_OUT_SET
    }

    # 1. Load from JSON config file if exists
    try:
        with open('NeuraConfig.json') as f:
            file_config = json.load(f)
            defaults.update(file_config)
    except FileNotFoundError:
        pass  # Use defaults if no config file

    # 2. Parse command line arguments (override JSON/defaults)
    # parser = argparse.ArgumentParser(description='Kernel processing configuration')
    # parser.add_argument('--do-mapping',
    #                    type=str_to_bool,
    #                    default=defaults["DO_MAPPING"],
    #                    help='Enable/disable mapping phase (default: True)')
    # args = parser.parse_args()

    # Update global configuration
    JSON_NAME = defaults["JSON_NAME"]
    KERNEL_DIRECTORY = defaults["KERNEL_DIRECTORY"]
    VECTOR_LANE = defaults["VECTOR_LANE"]
    DO_MAPPING = defaults["DO_MAPPING"]
    TIME_OUT_SET = defaults["TIME_OUT_SET"]


# Initialize configuration
load_configuration()


# ----------------------------------------------------------------------------
#   class defination                                                         /
# ----------------------------------------------------------------------------



class Kernel:
    def __init__(self, kernel_name, kernel_id, arrive_period, unroll_factor, vector_factor, total_iterations, cgra_rows, cgra_columns):
        """
        Initialize an instance of the Kernel class.

        Parameters:
            kernel_name (str): The name of the kernel.
            kernel_id (int): The ID of the kernel.
            arrive_period (int): The period at which the same kernel will arrive again.
            unroll_factor (int): The unroll factor of the kernel.
            vector_factor (int): The vector factor of the kernel.
            total_iterations (int): The total number of iterations of the kernel.
            cgra_rows (int): The number of rows in the CGRA.
            cgra_columns (int): The number of columns in the CGRA.
        """
        self.kernel_name = kernel_name
        self.kernel_id = kernel_id
        self.arrive_period = arrive_period
        self.unroll_factor = unroll_factor
        self.vector_factor = vector_factor
        self.df = pd.DataFrame(DICT_CSV, index=[0])
        self.base_ii = None  # II when using 1 CGRA, actual II, if fused, base_ii is fused_ii
        self.expandable_ii = None  # II when using 2 CGRAs, expandable II, if fused, expandable_ii is individual_ii
        self.utilization = None
        self.total_iterations = math.ceil(total_iterations / (self.unroll_factor*self.vector_factor))
        self.rows = cgra_rows
        self.columns = cgra_columns
        if DO_MAPPING:
            self.get_ii()  # Perform mapping and populate attributes
        else:
            self.read_ii()  # Read from existing csv

        # TODO
        print(f"Kernel {self.kernel_name} initialized with arrive_period={self.arrive_period}, unroll_factor={self.unroll_factor}")

    def __lt__(self, other):
        """
        Compare two Kernel by id.
        """
        return self.kernel_id < other.kernel_id

    def comp_kernel(self):
        """
        This is a func compile a kernel using clang with selected unrolling factor.

        Returns: function name of kernel.
        """
        file_source = (self.kernel_name.split("."))[0]

        if self.unroll_factor == 1 and self.vector_factor == 1:
            compile_command = f"clang-12 -emit-llvm -fno-unroll-loops -fno-vectorize -O3 -o kernel.bc -c {KERNEL_DIRECTORY}/{file_source}/{self.kernel_name}"
        elif self.unroll_factor == 1 and self.vector_factor != 1:
            compile_command = f"clang-12 -emit-llvm -fno-unroll-loops -O3 -mllvm -force-vector-width={self.vector_factor} -o kernel.bc -c {KERNEL_DIRECTORY}/{file_source}/{self.kernel_name}"
        elif self.unroll_factor != 1 and self.vector_factor == 1:
            compile_command = f"clang-12 -emit-llvm -funroll-loops -mllvm -unroll-count={self.unroll_factor} -fno-vectorize -O3 -o kernel.bc -c {KERNEL_DIRECTORY}/{file_source}/{self.kernel_name}"
        else:
            print("Error, invalid unroll and vector factor combination.")
            return

        compile_proc = subprocess.Popen([compile_command, '-u'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        (compile_out, compile_err) = compile_proc.communicate()

        disassemble_command = f"llvm-dis-12 kernel.bc -o kernel.ll"
        disassemble_proc = subprocess.Popen([disassemble_command, '-u'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        (disassemble_out, disassemble_err) = disassemble_proc.communicate()


        if compile_err:
            print(f"Compile warning message for {self.kernel_name}: {compile_err}")
        if disassemble_err:
            print(f"Disassemble error message for {self.kernel_name}: {disassemble_err}")
            return

        # collect the potentially targeting kernel/function from kernel.ll
        ir_file = open(f'kernel.ll', 'r')
        ir_lines = ir_file.readlines()

        # strips the newline character
        for line in ir_lines:
            if "define " in line and "{" in line and "@" in line:
                func_name = line.split("@")[1].split("(")[0]
                if "kernel" in func_name:
                    target_kernel = func_name
                    break

        ir_file.close()
        print(f"Target kernel function for {self.kernel_name}: {target_kernel}")
        return target_kernel

    def map_kernel(self):
        """
        This is a func for mapping a kernel and gain information during mapping.

        Returns: NULL
        """
        get_map_command = f"opt-12 -load ../build/src/libmapperPass.so -mapperPass kernel.bc"
        gen_map_proc = subprocess.Popen([get_map_command, "-u"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        dataS = []    # for get results from subprocess and output to pandas
        kernels_source = (self.kernel_name.split("."))[0]
        dataS.append(kernels_source)

        try:
            eventlet.monkey_patch()
            with eventlet.Timeout(TIME_OUT_SET, True):
                with gen_map_proc.stdout:
                    gen_map_proc.stdout.flush()
                    for line in iter(gen_map_proc.stdout.readline, b''):
                        output_line = line.decode("ISO-8859-1")
                        if "DFG node count: " in output_line:
                            dataS.append(int(output_line.split("DFG node count: ")[1].split(";")[0]))
                            dataS.append(int(output_line.split("DFG edge count: ")[1].split(";")[0]))
                        if "[RecMII: " in output_line:
                            dataS.append(int(output_line.split("[RecMII: ")[1].split("]")[0]))
                        if "[Mapping II: " in output_line:
                            self.base_ii = int(output_line.split("[Mapping II: ")[1].split("]")[0])
                            dataS.append(self.base_ii)
                        if "[ExpandableII: " in output_line:
                            self.expandable_ii = int(output_line.split("[ExpandableII: ")[1].split("]")[0])
                            dataS.append(self.expandable_ii)
                        if "tile avg fu utilization: " in output_line:
                            self.utilization = float(output_line.split("avg overall utilization: ")[1].split("%")[0])
                            dataS.append(self.utilization)
                        if "[Mapping Fail]" in output_line:
                            print(f"{self.kernel_name} mapping failed.")
        except eventlet.timeout.Timeout:
            dataS = [0]*(DICT_COLUMN)
            print("Skipping a specific config for kernel: ", self.kernel_name, "Because it runs more than", TIME_OUT_SET/60 , "minute(s).")

        if len(dataS) != DICT_COLUMN:
            dataS.extend([0]*(DICT_COLUMN-len(dataS)))

        self.df.loc[len(self.df.index)] = dataS

    def map_kernel_skip(self):
        """
        This is a func gain DFG information only without mapping.

        Returns: NULL
        """
        get_map_command = f"opt-12 -load ../../build/src/libmapperPass.so -mapperPass kernel.bc"
        gen_map_proc = subprocess.Popen([get_map_command, "-u"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        # Holds the results from subprocess and output to pandas.
        dataS = []
        kernels_source = (self.kernel_name.split("."))[0]
        dataS.append(kernels_source)
        # The first 4 element of dataS is not empty: kernelsSource, DFG node count, DFG edge count, RecMII.
        k_data_s_head = 4

        try:
            eventlet.monkey_patch()
            with eventlet.Timeout(TIME_OUT_SET, True):
                with gen_map_proc.stdout:
                    gen_map_proc.stdout.flush()
                    for line in iter(gen_map_proc.stdout.readline, b''):
                        output_line = line.decode("ISO-8859-1")
                        if "DFG node count: " in output_line:
                            dataS.append(int(output_line.split("DFG node count: ")[1].split(";")[0]))
                            dataS.append(int(output_line.split("DFG edge count: ")[1].split(";")[0]))
                        if "[RecMII: " in output_line:
                            dataS.append(int(output_line.split("[RecMII: ")[1].split("]")[0]))
                            dataS.extend([0]*(DICT_COLUMN-k_data_s_head))
                            break

        except eventlet.timeout.Timeout:
            dataS = [0]*(DICT_COLUMN)
            print("Skipping a specific config for kernel: ", self.kernel_name, "Because it runs more than", TIME_OUT_SET/60, "minute(s).")

        self.df.loc[len(self.df.index)] = dataS

    def get_ii(self):
        """
        This is a func to compile, run and map kernels under neura_json and store the mapping result in csv

        Returns: name of the csv that collects information of mapped kernels
        """
        csv_name = f'./tmp/t_{self.kernel_name}_{self.rows}x{self.columns}_unroll{self.unroll_factor}_vector{self.vector_factor}.csv'
        print("Generating", csv_name)
        target_kernel = self.comp_kernel()

        neura_json = {
            "kernel": target_kernel,
            "targetFunction": False,
            "targetNested": False,
            "targetLoopsID": [0],
            "doCGRAMapping": DO_MAPPING,
            "row": self.rows,
            "column": self.columns,
            "precisionAware": False,
            "heterogeneity"         : False,
            "isTrimmedDemo": True,
            "heuristicMapping": True,
            "parameterizableCGRA": False,
            "diagonalVectorization": False,
            "bypassConstraint": 4,
            "isStaticElasticCGRA": False,
            "ctrlMemConstraint": 10,
            "regConstraint": 8,
            "incrementalMapping"    : False,
            "vectorFactorForIdiv "  : 1,
            "testingOpcodeOffset"   : 0,
            "additionalFunc"        : {
                                        "complex-Ctrl" : [0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15]
                                    },
            "supportDVFS": False,
            "DVFSIslandDim": 1,
            "DVFSAwareMapping": False,
            "enablePowerGating": False,
            "expandableMapping" : True
        }

        json_object = json.dumps(neura_json, indent=4)

        with open(JSON_NAME, "w") as outfile:
            outfile.write(json_object)
        if DO_MAPPING:
            self.map_kernel()
        else:
            self.map_kernel_skip()

        self.df.to_csv(csv_name)
        return csv_name

    def read_ii(self):
        """
        This is a func to read from csv generated from get_ii()

        Returns: csv_name
        """
        if self.vector_factor > 8:
            csv_name = f'./tmp/t_{self.kernel_name}_{self.rows}x{self.columns}_unroll{self.unroll_factor}_vector8.csv'
        else:
            csv_name = f'./tmp/t_{self.kernel_name}_{self.rows}x{self.columns}_unroll{self.unroll_factor}_vector{self.vector_factor}.csv'

        try:
            df = pd.read_csv(csv_name)
            self.base_ii = int(df['mappingII'].iloc[1])
            self.expandable_ii = int(df['expandableII'].iloc[1])
            self.utilization = float(df['utilization'].iloc[1])/100
        except FileNotFoundError:
            print(f"CSV file {csv_name} not found.")
        except ValueError:
            print(f"Error extracting II values from {csv_name}.")

        return csv_name

    def return_ii(self, num_cgras):
        """
        Get the initiation interval (II) based on the number of CGRAs allocated.

        Parameters:
            num_cgras (int): Number of CGRAs allocated.

        Returns:
            int: The initiation interval (II).
        """
        if num_cgras == 1:
            return self.base_ii
        elif num_cgras == 2:
            return self.expandable_ii
        else:
            raise ValueError("Number of CGRAs must be 1 or 2.")

    def return_total_iterations(self):
        """
        Total iterations for the kernel, affected by unroll_factor and vector_factor

        Returns:
            int: Total iterations.
        """
        return self.total_iterations

    def create_instance(self, arrival_time):
        """
        Create a KernelInstance based on the current kernel.

        Parameters:
            arrival_time (int): The time at which the instance arrives.

        Returns:
            KernelInstance: A new instance of the kernel.
        """
        return KernelInstance(self, arrival_time)


class KernelInstance:
    def __init__(self, kernel, arrival_time):
        """
        Initialize a KernelInstance.

        Parameters:
            kernel (Kernel): The kernel from which this instance is created.
            arrival_time (int): The time at which the instance arrives.
        """
        self.kernel = kernel
        self.arrival_time = arrival_time
        self.start_time = None
        self.allocated_cgras = 0
        self.ii = None
        self.end_time = None
        self.is_valid = True
        self.pure_execution_duration = 0  # Track pure execution duration for this instance
        self.pure_waiting_duration = 0  # Track pure waiting duration for this instance
        # Determine the maximum number of CGRAs that can be allocated
        if self.kernel.vector_factor == 1:
            self.max_allocate_cgra = 2
        else:
            self.max_allocate_cgra = math.ceil(self.kernel.vector_factor/VECTOR_LANE)

    def __lt__(self, other):
        """
        Compare two KernelInstance instances by arrival time.
        """
        return self.arrival_time < other.arrival_time

    def calculate_execution_duration(self):
        """
        Calculate the execution duration based on the number of allocated CGRAs
        at the beginning running time of current kernel. It may change after.

        Returns:
            int: Total execution duration in cycles.
        """
        if self.kernel.vector_factor == 1:
            if self.allocated_cgras == 1:
                self.ii = self.kernel.base_ii
            elif self.allocated_cgras == 2:
                self.ii = self.kernel.expandable_ii
            else:
                raise ValueError(f"Number of CGRAs must be between 1 and {self.max_allocate_cgra}.")
            execution_duration = self.kernel.total_iterations * self.ii
        else:
            self.ii = self.kernel.base_ii
            execution_duration = math.ceil(self.kernel.total_iterations * self.ii * (self.kernel.vector_factor / (VECTOR_LANE * self.allocated_cgras)))
            print(self.kernel.vector_factor / (VECTOR_LANE * self.allocated_cgras))
        print(f"Calculated execution duration for {self.kernel.kernel_name}: {execution_duration} cycles (II={self.ii}, iterations={self.kernel.total_iterations})")
        return execution_duration

    def copy_with_valid(self):
        """
        Create a copy of the current instance and set is_valid to True.

        Returns:
            KernelInstance: A new instance copy.
        """
        new_instance = KernelInstance(self.kernel, self.arrival_time)
        new_instance.start_time = self.start_time
        new_instance.allocated_cgras = self.allocated_cgras
        new_instance.ii = self.ii
        new_instance.end_time = self.end_time
        new_instance.is_valid = True
        new_instance.pure_execution_duration = 0
        new_instance.pure_waiting_duration = self.pure_waiting_duration
        new_instance.max_allocate_cgra = self.max_allocate_cgra
        return new_instance


if __name__ == "__main__":
    baselineCase1=[
        [
            # Kernel(kernel_name="fft.c", kernel_id=4, arrive_period=3840000, unroll_factor=1, vector_factor=1, total_iterations=480000, cgra_rows=4, cgra_columns=4),
            # Kernel(kernel_name="dtw.cpp", kernel_id=5, arrive_period=3932160, unroll_factor=1, vector_factor=1, total_iterations=524288, cgra_rows=4, cgra_columns=4),
            # Kernel(kernel_name="fft.c", kernel_id=4, arrive_period=3840000, unroll_factor=1, vector_factor=4, total_iterations=480000, cgra_rows=4, cgra_columns=4),
            # Kernel(kernel_name="dtw.cpp", kernel_id=5, arrive_period=3932160, unroll_factor=1, vector_factor=4, total_iterations=524288, cgra_rows=4, cgra_columns=4),
            # Kernel(kernel_name="fft.c", kernel_id=4, arrive_period=3840000, unroll_factor=1, vector_factor=8, total_iterations=480000, cgra_rows=4, cgra_columns=4),
            # Kernel(kernel_name="dtw.cpp", kernel_id=5, arrive_period=3932160, unroll_factor=1, vector_factor=8, total_iterations=524288, cgra_rows=4, cgra_columns=4),
            # Kernel(kernel_name="fft.c", kernel_id=4, arrive_period=3840000, unroll_factor=1, vector_factor=16, total_iterations=480000, cgra_rows=4, cgra_columns=4),
            # Kernel(kernel_name="dtw.cpp", kernel_id=5, arrive_period=3932160, unroll_factor=1, vector_factor=16, total_iterations=524288, cgra_rows=4, cgra_columns=4),
            Kernel(kernel_name="fft.c", kernel_id=4, arrive_period=3840000, unroll_factor=2, vector_factor=1, total_iterations=480000, cgra_rows=4, cgra_columns=4),
            Kernel(kernel_name="dtw.cpp", kernel_id=5, arrive_period=3932160, unroll_factor=2, vector_factor=1, total_iterations=524288, cgra_rows=4, cgra_columns=4),
            Kernel(kernel_name="fft.c", kernel_id=4, arrive_period=3840000, unroll_factor=4, vector_factor=1, total_iterations=480000, cgra_rows=4, cgra_columns=4),
            Kernel(kernel_name="dtw.cpp", kernel_id=5, arrive_period=3932160, unroll_factor=4, vector_factor=1, total_iterations=524288, cgra_rows=4, cgra_columns=4),
            # Kernel(kernel_name="fft.c", kernel_id=4, arrive_period=3840000, unroll_factor=1, vector_factor=1, total_iterations=480000, cgra_rows=12, cgra_columns=12),
            # Kernel(kernel_name="dtw.cpp", kernel_id=5, arrive_period=3932160, unroll_factor=1, vector_factor=1, total_iterations=524288, cgra_rows=12, cgra_columns=12),
            # Kernel(kernel_name="fft.c", kernel_id=4, arrive_period=3840000, unroll_factor=1, vector_factor=4, total_iterations=480000, cgra_rows=12, cgra_columns=12),
            # Kernel(kernel_name="dtw.cpp", kernel_id=5, arrive_period=3932160, unroll_factor=1, vector_factor=4, total_iterations=524288, cgra_rows=12, cgra_columns=12),
            # Kernel(kernel_name="fft.c", kernel_id=4, arrive_period=3840000, unroll_factor=1, vector_factor=8, total_iterations=480000, cgra_rows=12, cgra_columns=12),
            # Kernel(kernel_name="dtw.cpp", kernel_id=5, arrive_period=3932160, unroll_factor=1, vector_factor=8, total_iterations=524288, cgra_rows=12, cgra_columns=12),
            # Kernel(kernel_name="fft.c", kernel_id=4, arrive_period=3840000, unroll_factor=1, vector_factor=16, total_iterations=480000, cgra_rows=12, cgra_columns=12),
            # Kernel(kernel_name="dtw.cpp", kernel_id=5, arrive_period=3932160, unroll_factor=1, vector_factor=16, total_iterations=524288, cgra_rows=12, cgra_columns=12),
            Kernel(kernel_name="fft.c", kernel_id=4, arrive_period=3840000, unroll_factor=2, vector_factor=1, total_iterations=480000, cgra_rows=12, cgra_columns=12),
            Kernel(kernel_name="dtw.cpp", kernel_id=5, arrive_period=3932160, unroll_factor=2, vector_factor=1, total_iterations=524288, cgra_rows=12, cgra_columns=12),
            Kernel(kernel_name="fft.c", kernel_id=4, arrive_period=3840000, unroll_factor=4, vector_factor=1, total_iterations=480000, cgra_rows=12, cgra_columns=12),
            Kernel(kernel_name="dtw.cpp", kernel_id=5, arrive_period=3932160, unroll_factor=4, vector_factor=1, total_iterations=524288, cgra_rows=12, cgra_columns=12),
        ]
    ]

