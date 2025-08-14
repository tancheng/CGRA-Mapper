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
KERNEL_DIRECTORY = "../../test/kernels"
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
        print(f"Kernel {self.kernel_name} initialized with arrive_period={self.arrive_period}, unroll_factor={self.unroll_factor}, vector_factor={self.vector_factor}")

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
        elif self.kernel_name == "conv.c" and self.unroll_factor == 4:
            print(1)
            compile_command = f"clang-12 -emit-llvm -funroll-loops -mllvm -unroll-count={self.unroll_factor} -fno-slp-vectorize -O3 -o kernel.bc -c {KERNEL_DIRECTORY}/{file_source}/{self.kernel_name}"
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
        get_map_command = f"opt-12 -load ../../build/src/libmapperPass.so -mapperPass kernel.bc"
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
            "doCGRAMapping": True,
            "row": self.rows,
            "column": self.columns,
            "precisionAware": False,
            "fusionStrategy": ["default_heterogeneous"],   # TODO: 有一些 kernel 删去 "default_heterogeneous"
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
                                        "complex-Ctrl" : [0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15],
                                        "fptosi": [0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15],
                                        "complex-BrT" : [4,5,6,7],
                                        "complex-CoT" : [8,9,10,11]
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
        if True:
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
        # 计算 CSV 文件路径，根据 kernel_name 是否为特定值使用不同的前缀
        prefix = './tmp/fftDtw/t_' if self.kernel_name in {'fft.c', 'dtw.cpp'} else './tmp/t_'
        csv_name = f'{prefix}{self.kernel_name}_{self.rows}x{self.columns}_unroll{self.unroll_factor}_vector{self.vector_factor}.csv'

        try:
            df = pd.read_csv(csv_name)
            self.base_ii = int(df['mappingII'].iloc[1])
            self.expandable_ii = int(df['expandableII'].iloc[1])
            # 检查是否存在utilization列
            if 'utilization' in df.columns:
                self.utilization = float(df['utilization'].iloc[1]) / 100
            else:
                self.get_ii()
                return csv_name
        except FileNotFoundError:
            print(f"CSV file {csv_name} not found.")
            self.get_ii()
            return csv_name
        except ValueError:
            print(f"Error extracting II values from {csv_name}.")
            self.get_ii()
            return csv_name

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
            execution_duration = self.kernel.total_iterations * self.ii * math.ceil(self.kernel.vector_factor / (VECTOR_LANE * self.allocated_cgras))
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


class SystemIdleTracker:
    def __init__(self, num_cgras):
        """Initialize the system idle time tracker

        Args:
            num_cgras: Total number of CGRAs in the system
        """
        self.num_cgras = num_cgras
        self.last_active_time = 0  # Timestamp when system was last active
        self.idle_periods = []     # List to store idle periods (start, end)

    def check_idle_period(self, current_time, available_cgras):
        """Check and record idle periods

        Args:
            current_time: Current simulation time (passed from simulate function)
            available_cgras: Number of currently available CGRAs
        """
        # Detect system-wide idle state (all CGRAs available)
        if available_cgras == self.num_cgras and current_time > self.last_active_time:
            self.idle_periods.append((self.last_active_time, current_time))
        else:
            # Update last active time if system is not fully idle
            self.last_active_time = current_time

    @property
    def total_idle_duration(self) -> int:
        """Calculate total accumulated idle time

        Returns:
            Sum of all idle periods in cycles
        """
        return sum(end - start for start, end in self.idle_periods)  # Fixed typo: idle_periods

    def get_utilization(self, total_cgra_runtime, current_time) -> float:
        """Calculate system utilization rate

        Args:
            total_cgra_runtime: Sum of busy time across all CGRAs
            current_time: Current simulation time

        Returns:
            Utilization percentage (0.0 to 1.0)
        """
        if current_time <= 0:
            return 0.0
        # Utilization = Actual busy time / Possible busy time
        possible_busy_time = (current_time - self.total_idle_duration) * self.num_cgras
        print(f"Total idle duration is {self.total_idle_duration}, total_cgra_runtime is {total_cgra_runtime}")
        return total_cgra_runtime / possible_busy_time if possible_busy_time > 0 else 0.0

# ----------------------------------------------------------------------------
#   function defination                                                      /
# ----------------------------------------------------------------------------

def allocate(priority_boosting, instance, current_time, available_cgras, events, running_instances, runned_kernel_names, total_cgra_runtime):
    """
    Allocate CGRAs to a kernel instance.

    Parameters:
        instance (KernelInstance): The kernel instance to allocate CGRAs to.
        current_time (int): The current simulation time.
        available_cgras (int): The number of available CGRAs.
        events (list): The event queue.
        running_instances (list): The list of currently running instances.
        runned_kernel_names (list): The list of names of the kernels that have been run.
        total_cgra_runtime (float): The total runtime of all CGRAs.

    Returns:
        int: The updated number of available CGRAs.
        float: The updated total runtime of all CGRAs.
    """
    runned_kernel_names.append(instance.kernel.kernel_name)
    # HACK：再检查一下 cgra 利用率的问题，已经通过 invalid 查看解决
    # 如果kernel名称中包含"+"，则将分配的CGRAs数量限制为1

    if priority_boosting == 0:
        # Noboosting 还是给点限制吧
        if '+' in instance.kernel.kernel_name:
            allocate_cgras = min(1, available_cgras)
            print(f"Kernel {instance.kernel.kernel_name} contains '+', limiting allocation to 1 CGRA")
        elif instance.kernel.vector_factor != 1:    # vector 的一定要限制
            allocate_cgras = min(1, available_cgras)
            print(f"Kernel {instance.kernel.kernel_name} is vectorized, limiting allocation to 1 CGRA")
        elif available_cgras < 6:   # scalar 用这个限制，试过了，1的限制不是很好，会导致 noboosting 比 baseline 差一点
            allocate_cgras = min(1, available_cgras)
            print(f"available_cgras is less than 5, limiting allocation to 1 CGRA")
        else:
            allocate_cgras = min(instance.max_allocate_cgra, available_cgras)
        #allocate_cgras = 1
    else:
        allocate_cgras = 1
    available_cgras -= allocate_cgras
    instance.start_time = current_time
    instance.allocated_cgras = allocate_cgras
    execution_duration = instance.calculate_execution_duration()
    instance.end_time = current_time + execution_duration
    instance.pure_waiting_duration = instance.start_time - instance.arrival_time  # Record pure waiting time
    print(f"Allocated {allocate_cgras} CGRAs to {instance.kernel.kernel_name} at {current_time}. Execution will end at {instance.end_time}")
    heapq.heappush(events, (instance.end_time, 'end', instance, instance))
    running_instances.append(instance)
    if instance.kernel.rows == 12 and instance.kernel.columns == 12:
        total_cgra_runtime += allocate_cgras * execution_duration * instance.kernel.utilization
    else:
        total_cgra_runtime += allocate_cgras * execution_duration
    return available_cgras, total_cgra_runtime


def release(instance, current_time, available_cgras, running_instances, completed_instances, kernel_latency, total_cgra_runtime):
    """
    Release the CGRAs occupied by a kernel instance.

    Parameters:
        instance (KernelInstance): The kernel instance to release CGRAs from.
        current_time (int): The current simulation time.
        available_cgras (int): The number of available CGRAs.
        running_instances (list): The list of currently running instances.
        completed_instances (list): The list of completed instances.
        kernel_latency (dict): A dictionary used to track the total latency of each kernel.
        total_cgra_runtime (float): The total runtime of all CGRAs.

    Returns:
        int: The updated number of available CGRAs.
        float: The updated total runtime of all CGRAs.
    """
    available_cgras += instance.allocated_cgras
    completed_instances.append(instance)
    if instance in running_instances:
        running_instances.remove(instance)
    # Update per-kernel overall latency
    instance.end_time = current_time
    latency = instance.end_time - instance.start_time
    instance.pure_execution_duration = instance.end_time - instance.start_time  # Record pure execution time
    kernel_latency[instance.kernel.kernel_name] += latency
    print(f"Released {instance.allocated_cgras} CGRAs from {instance.kernel.kernel_name} at {current_time}. Latency added: {latency} cycles")
    return available_cgras, total_cgra_runtime


def re_allocate(instance, current_time, available_cgras, events, total_cgra_runtime):
    """
    Re-allocate additional CGRAs to a kernel instance if possible.

    Parameters:
        instance (KernelInstance): The kernel instance to re-allocate CGRAs to.
        available_cgras (int): Number of available CGRAs.
        events (list): The event queue.
        current_time (int): The current simulation time.
        total_cgra_runtime (float): Total runtime of all CGRAs.

    Returns:
        int: Updated number of available CGRAs.
        float: Updated total runtime of all CGRAs.
    """
    if not instance.is_valid:
        # TODO: 把 Invalid 去除在 running_instance 以外
        #print(f"Instance {instance.kernel.kernel_name} is already invalid, skipping re-allocation.")
        return available_cgras, total_cgra_runtime
    if instance.allocated_cgras < instance.max_allocate_cgra and available_cgras > 0:
        possible_alloc = min(instance.max_allocate_cgra - instance.allocated_cgras, available_cgras)
        original_allocated_cgras = instance.allocated_cgras
        # Update allocation
        instance.allocated_cgras += possible_alloc
        available_cgras -= possible_alloc
        # Recalculate remaining iterations
        elapsed_duration = current_time - instance.start_time
        # 计算等效标量迭代次数（考虑向量化和CGRAs）
        # 使用原始分配的CGRAs和II计算已完成的等效标量迭代
        if instance.kernel.vector_factor == 1:
            # 标量情况
            completed_iters = elapsed_duration // instance.ii
        else:
            # 向量情况 - 考虑向量化效率
            effective_ii = instance.ii * math.ceil(instance.kernel.vector_factor / (VECTOR_LANE * original_allocated_cgras))
            completed_iters = int(elapsed_duration // effective_ii)
        remaining_iters = instance.kernel.total_iterations - completed_iters
        print(f"current_time {current_time}, completed_iters {completed_iters}")
        # Update II and remaining_execution_duration
        if instance.kernel.vector_factor == 1:
            # Scalar case
            if instance.allocated_cgras == 1:
                instance.ii = instance.kernel.base_ii
            elif instance.allocated_cgras == 2:
                instance.ii = instance.kernel.expandable_ii
            else:
                raise ValueError(f"Number of CGRAs must be between 1 and {instance.max_allocate_cgra}.")
            remaining_execution_duration = remaining_iters * instance.ii
        else:
            # Vector case
            vector_divisor = VECTOR_LANE * instance.allocated_cgras
            remaining_execution_duration = remaining_iters * instance.ii * math.ceil(instance.kernel.vector_factor / vector_divisor)
        # Schedule new end event
        new_end_time = current_time + remaining_execution_duration
        print(f"remaining_iters {remaining_iters}, remaining_execution_duration {remaining_execution_duration}")
        print(f"Re-allocated succeed. {instance.kernel.kernel_name}. Add {possible_alloc} CGRAs at {current_time}. Old end time: {instance.end_time}. New end time: {new_end_time}")
        # Create a new valid instance for the new end event
        new_instance = instance.copy_with_valid()  # Assume there is a copy method in KernelInstance class
        heapq.heappush(events, (new_end_time, 'end', new_instance, new_instance))
        # Invalidate old end event by leaving it in the heap but ignoring when processed
        instance.is_valid = False   # Old instance is invalid
        # 修正total_cgra_runtime计算，添加utilization判断
        kernel = instance.kernel
        is_12x12 = (kernel.rows == 12 and kernel.columns == 12)
        utilization_factor = kernel.utilization if is_12x12 else 1.0
        # 统一应用利用率因子
        old_estimate = original_allocated_cgras * (instance.end_time - instance.start_time) * utilization_factor
        actual_runtime = original_allocated_cgras * elapsed_duration * utilization_factor
        new_allocation_runtime = instance.allocated_cgras * remaining_execution_duration * utilization_factor
        # 更新总运行时间
        total_cgra_runtime -= old_estimate  # 移除旧的估计值
        total_cgra_runtime += actual_runtime  # 添加实际已经运行时间
        total_cgra_runtime += new_allocation_runtime  # 添加新的分配运行时间
    else:
        print(f"Re-allocated Failed. ({instance.kernel.kernel_name} at time {current_time})")
    return available_cgras, total_cgra_runtime


def handle_reallocation(priority_boosting, running, current_time, available_cgras, events, total_cgra_runtime):
    """
    Checks if a running instance should be re-allocated based on the priority_boosting strategy.

    Args:
        priority_boosting (int): The strategy for re-allocation.
                                 0: No re-allocation.
                                 1: Re-allocate for vector_factor=1 kernels without '+' in name.
                                 2: Re-allocate for all vector_factor=1 kernels.
                                 3: Re-allocate for all kernels.
        running (object): The currently running instance to check.
        current_time (float): The current simulation time.
        available_cgras (int): The number of currently available CGRAs.
        events (list): The list of simulation events.
        total_cgra_runtime (float): The accumulated total CGRA runtime.

    Returns:
        tuple: A tuple containing the updated available_cgras and total_cgra_runtime.
    """
    if priority_boosting <= 0:
        return available_cgras, total_cgra_runtime

    should_reallocate = False
    kernel_info = running.kernel

    if priority_boosting == 1:
        # Re-allocate only for kernels with vector_factor=1 and no '+' in the name
        should_reallocate = (kernel_info.vector_factor == 1 and '+' not in kernel_info.kernel_name)
    elif priority_boosting == 2:
        # Re-allocate for all kernels with vector_factor=1 (including those with '+')
        should_reallocate = (kernel_info.vector_factor == 1)
    elif priority_boosting == 3:
        # Re-allocate for all kernels
        should_reallocate = True

    # If the condition is met, perform the re-allocation
    if should_reallocate:
        available_cgras, total_cgra_runtime = re_allocate(
            running, current_time, available_cgras, events, total_cgra_runtime
        )

    return available_cgras, total_cgra_runtime

def simulate(num_cgras, kernels, priority_boosting, lcm_time=262144):
    """
    lcm_time=40000000
    Simulate the execution of multiple kernels on a CGRA architecture.

    Parameters:
        num_cgras (int): The number of CGRAs in the CGRA architecture.
        kernels (list of Kernel): The list of kernels to simulate.
        priority_boosting (bool): Whether to enable priority boosting.
        lcm_time (int): The least common multiple of the arrival periods.

    Returns:
        dict: A dictionary that maps kernel names to their total latencies.
    """
    available_cgras = num_cgras
    events = []  # when a kernel arrives or ends, it is an event
    current_time = 0
    waiting_instances = []
    running_instances = []
    completed_instances = []
    runned_kernel_names = []
    # Dictionary to store per-kernel arrival times
    kernel_arrival_count = {kernel.kernel_name: 0 for kernel in kernels}
    # Dictionary to store per-kernel overall latency (cycle)
    kernel_latency = {kernel.kernel_name: 0 for kernel in kernels}
    # Dictionary to store per-kernel execution duration distribution
    kernel_execution_distribution = {kernel.kernel_name: [] for kernel in kernels}
    # Dictionary to store per-kernel waiting duration distribution
    kernel_waiting_distribution = {kernel.kernel_name: [] for kernel in kernels}
    # Dictionary to store per-kernel ratio (iterations per cycle)
    kernel_execution_ratio = {kernel.kernel_name: 0 for kernel in kernels}
    # Dictionary to store per-kernel ratio (iterations per cycle)
    kernel_waiting_ratio = {kernel.kernel_name: 0 for kernel in kernels}
    total_cgra_runtime = 0
    idle_tracker = SystemIdleTracker(num_cgras=num_cgras)
    arrive_times_list = {
        kernel.kernel_name: max(3, (lcm_time // kernel.arrive_period))
        for kernel in kernels
    }


    print(f"\033[91mPriority Boosting Level: {priority_boosting}\033[0m")

    for kernel in kernels:
        print(f"Kernel {kernel.kernel_name} base_ii={kernel.base_ii}, expandable_ii={kernel.expandable_ii}, \
              iterations={kernel.total_iterations}, utilization={kernel.utilization}, arrive_times, {arrive_times_list[kernel.kernel_name]}")

    # Schedule initial arrivals for all kernels
    for kernel in kernels:
        first_arrival = 0
        # heapq keeps a priority queue that contains (event_arrive_end_time (int), event_type (str), Kernel, KernelInstance (needed when 'end'))
        heapq.heappush(events, (first_arrival, 'arrival', kernel, None))

    while events:
        event_time, event_type, kernel_or_instance, _ = heapq.heappop(events)
        if event_type == 'end' and not kernel_or_instance.is_valid:
            print(f"Skipping invalid event for {kernel_or_instance.kernel.kernel_name}")
            continue

        current_time = event_time
        print("="*20)
        idle_tracker.check_idle_period(current_time, available_cgras)
        print(f"Processing event at time {current_time}: type={event_type}, kernel={kernel_or_instance.kernel_name if event_type == 'arrival' else kernel_or_instance.kernel.kernel_name}")

        if event_type == 'arrival':
            kernel = kernel_or_instance
            kernel_arrival_count[kernel.kernel_name] += 1
            # Create a new instance
            instance = kernel.create_instance(current_time)
            # Schedule next arrival if within lcm_time
            next_arrival = current_time + kernel.arrive_period
            if kernel_arrival_count[kernel.kernel_name] < arrive_times_list[kernel.kernel_name]:
                heapq.heappush(events, (next_arrival, 'arrival', kernel, None))
                print(f"Scheduled next arrival for {kernel.kernel_name} at time {next_arrival}")


            # Try to allocate CGRAs
            if available_cgras >= 1:
                available_cgras, total_cgra_runtime = allocate(priority_boosting, instance, current_time, available_cgras, events, running_instances, runned_kernel_names, total_cgra_runtime)
                available_cgras, total_cgra_runtime = handle_reallocation(priority_boosting, instance, current_time, available_cgras, events, total_cgra_runtime)
            else:
                waiting_instances.append(instance)
                print(f"No available CGRAs for {kernel.kernel_name}. Added to waiting queue.")

        elif event_type == 'end':
            instance = kernel_or_instance
            # Release CGRAs
            available_cgras, total_cgra_runtime = release(instance, current_time, available_cgras, running_instances, completed_instances,kernel_latency, total_cgra_runtime)

            # Update execution duration distribution
            kernel_execution_distribution[instance.kernel.kernel_name].append(instance.pure_execution_duration)
            kernel_waiting_distribution[instance.kernel.kernel_name].append(instance.pure_waiting_duration)

            # Check waiting queue
            while waiting_instances and available_cgras >= 1:
                instance = waiting_instances.pop(0)
                print(f"Allocating CGRAs to waiting instance {instance.kernel.kernel_name}")
                available_cgras, total_cgra_runtime = allocate(priority_boosting, instance, current_time, available_cgras, events, running_instances, runned_kernel_names, total_cgra_runtime)
                available_cgras, total_cgra_runtime = handle_reallocation(priority_boosting, instance, current_time, available_cgras, events, total_cgra_runtime)

            # Check running instances for possible re-allocation
            # if priority_boosting:
            #     for running in running_instances:
            #         available_cgras, total_cgra_runtime = re_allocate(running, current_time, available_cgras, events, total_cgra_runtime)
            for running in running_instances[:]:
                available_cgras, total_cgra_runtime = handle_reallocation(
                    priority_boosting, running, current_time, available_cgras, events, total_cgra_runtime
                )
        print("="*20)

    overall_execution = 0
    overall_waiting = 0
    # Calculate ratio for each kernel
    for kernel in kernels:
        total_execution_duration = sum(
            [inst.pure_execution_duration for inst in completed_instances if inst.kernel.kernel_name == kernel.kernel_name])
        total_waiting_duration = sum(
            [inst.pure_waiting_duration for inst in completed_instances if inst.kernel.kernel_name == kernel.kernel_name])
        total_duration = total_execution_duration + total_waiting_duration
        kernel_execution_ratio[kernel.kernel_name] = total_execution_duration / total_duration if total_duration > 0 else 0
        kernel_waiting_ratio[kernel.kernel_name] = total_waiting_duration / total_duration if total_duration > 0 else 0
        overall_execution += total_execution_duration
        overall_waiting += total_waiting_duration

    # Calculate utilization of total CGRAs
    cgra_utilization = idle_tracker.get_utilization(total_cgra_runtime, current_time)
    overall_latency = current_time  # when all kernels are done

    print(f"Simulation completed. Kernel latencies: {kernel_latency}")
    print(f"Kernel execution_ratio: {kernel_execution_ratio}")
    print(f"Kernel execution duration distributions: {kernel_execution_distribution}")
    print(f"Kernel Runned List: {runned_kernel_names}")
    print(f"CGRA utilization: {cgra_utilization}")
    print(f"overall latency: {overall_latency}")
    print(f"overall execution: {overall_execution}")
    print(f"overall waiting: {overall_waiting}")
    return kernel_latency, kernel_waiting_distribution, kernel_execution_ratio, kernel_waiting_ratio, kernel_execution_distribution, cgra_utilization, overall_latency


def run_multiple_simulations_and_save_to_csv(kernels_list, csvname, priority_boosting, kernel_case, num_cgras=9):
    """
    Run multiple simulations and save the results to a CSV file.

    Parameters:
        kernels_list (list of list of Kernel): A list of kernels.
        csvname (str): The name of the CSV file.
        priority_boosting (int): Whether to enable priority boosting.
        num_cgras (int): The number of CGRAs, default 9.
    """
    for i, kernels in enumerate(kernels_list, start = 1):
        kernel_latency, kernel_waiting_distribution, kernel_execution_ratio, kernel_waiting_ratio, kernel_execution_distribution, cgra_utilization, overall_latency = simulate(num_cgras, kernels, priority_boosting)

        # Calculate fastest, slowest, and average execution duration per kernel
        execution_stats = {}
        for kernel_name, execution_durations in kernel_execution_distribution.items():
            if execution_durations:
                fastest = min(execution_durations)
                slowest = max(execution_durations)
                average = sum(execution_durations) / len(execution_durations)
                total = sum(execution_durations)
                execution_stats[kernel_name] = {
                    "fastest_execution_duration": fastest,
                    "slowest_execution_duration": slowest,
                    "average_execution_duration": average,
                    "total_execution_duration": total
                }

        # Calculate fastest, slowest, and average waiting duration per kernel
        waiting_stats = {}
        for kernel_name, waiting_durations in kernel_waiting_distribution.items():
            if waiting_durations:
                fastest = min(waiting_durations)
                slowest = max(waiting_durations)
                average = sum(waiting_durations) / len(waiting_durations)
                total = sum(waiting_durations)
                waiting_stats[kernel_name] = {
                    "fastest_waiting_duration": fastest,
                    "slowest_waiting_duration": slowest,
                    "average_waiting_duration": average,
                    "total_waiting_duration": total
                }

        all_results = []
        for kernel in kernels:
            kernel_name = kernel.kernel_name
            result = {
                "Kernel_Name": kernel_name,
                "Arrive_Period": kernel.arrive_period,
                "Unroll_Factor": kernel.unroll_factor,
                "Vector_Factor": kernel.vector_factor,
                "fastest_execution_duration": execution_stats.get(kernel_name, {}).get("fastest_execution_duration", None),
                "slowest_execution_duration": execution_stats.get(kernel_name, {}).get("slowest_execution_duration", None),
                "Average_Execution_duration": execution_stats.get(kernel_name, {}).get("average_execution_duration", None),
                "fastest_waiting_duration": waiting_stats.get(kernel_name, {}).get("fastest_waiting_duration", None),
                "slowest_waiting_duration": waiting_stats.get(kernel_name, {}).get("slowest_waiting_duration", None),
                "Average_Waiting_duration": waiting_stats.get(kernel_name, {}).get("average_waiting_duration", None),
                "Total_Execution_duration": execution_stats.get(kernel_name, {}).get("total_execution_duration", None),
                "Total_Waiting_duration": waiting_stats.get(kernel_name, {}).get("total_waiting_duration", None),
                "Execution_duration Ratio": kernel_execution_ratio[kernel_name],
                "Waiting_duration Ratio": kernel_waiting_ratio[kernel_name],
                "Overall_Case_Latency": overall_latency,
                "CGRA_Utilization": cgra_utilization,
                "Total_Execution_duration Ratio": (execution_stats.get(kernel_name, {}).get("total_execution_duration", None))/overall_latency,
                "Total_Waiting_duration Ratio": (waiting_stats.get(kernel_name, {}).get("total_waiting_duration", None))/overall_latency,
                "Total_Latency Ratio":  (execution_stats.get(kernel_name, {}).get("total_execution_duration", None) + waiting_stats.get(kernel_name, {}).get("total_waiting_duration", None))/overall_latency
            }
            all_results.append(result)


        df = pd.DataFrame(all_results)
        file_name = f'./result/simulation_{kernel_case}_{csvname}.csv'
        df.to_csv(file_name, index=False)


if __name__ == "__main__":
    baselineCase1=[
        [
            #Kernel(kernel_name="fir.cpp", kernel_id=8, arrive_period=600000, unroll_factor=1, vector_factor=8, total_iterations=300000, cgra_rows=4, cgra_columns=4),
            Kernel(kernel_name="spmv.c", kernel_id=3, arrive_period=3600000, unroll_factor=1, vector_factor=1, total_iterations=1200000, cgra_rows=12, cgra_columns=12),
            Kernel(kernel_name="spmv.c", kernel_id=3, arrive_period=3600000, unroll_factor=2, vector_factor=1, total_iterations=1200000, cgra_rows=12, cgra_columns=12),
            Kernel(kernel_name="spmv.c", kernel_id=3, arrive_period=3600000, unroll_factor=4, vector_factor=1, total_iterations=1200000, cgra_rows=12, cgra_columns=12),
            Kernel(kernel_name="spmv.c", kernel_id=3, arrive_period=3600000, unroll_factor=1, vector_factor=8, total_iterations=1200000, cgra_rows=4, cgra_columns=4),
            Kernel(kernel_name="spmv.c", kernel_id=3, arrive_period=3600000, unroll_factor=1, vector_factor=4, total_iterations=1200000, cgra_rows=4, cgra_columns=4),
            Kernel(kernel_name="spmv.c", kernel_id=3, arrive_period=3600000, unroll_factor=1, vector_factor=16, total_iterations=1200000, cgra_rows=4, cgra_columns=4),
            Kernel(kernel_name="gemm.c", kernel_id=3, arrive_period=3600000, unroll_factor=1, vector_factor=1, total_iterations=1200000, cgra_rows=12, cgra_columns=12),
            Kernel(kernel_name="gemm.c", kernel_id=3, arrive_period=3600000, unroll_factor=2, vector_factor=1, total_iterations=1200000, cgra_rows=12, cgra_columns=12),
            Kernel(kernel_name="gemm.c", kernel_id=3, arrive_period=3600000, unroll_factor=4, vector_factor=1, total_iterations=1200000, cgra_rows=12, cgra_columns=12),
            Kernel(kernel_name="gemm.c", kernel_id=3, arrive_period=3600000, unroll_factor=1, vector_factor=1, total_iterations=1200000, cgra_rows=4, cgra_columns=4),
            Kernel(kernel_name="spmv.c", kernel_id=3, arrive_period=3600000, unroll_factor=1, vector_factor=8, total_iterations=1200000, cgra_rows=4, cgra_columns=4),
            Kernel(kernel_name="spmv.c", kernel_id=3, arrive_period=3600000, unroll_factor=1, vector_factor=4, total_iterations=1200000, cgra_rows=4, cgra_columns=4),
            Kernel(kernel_name="spmv.c", kernel_id=3, arrive_period=3600000, unroll_factor=1, vector_factor=16, total_iterations=1200000, cgra_rows=4, cgra_columns=4),
            Kernel(kernel_name="gemm.c", kernel_id=3, arrive_period=3600000, unroll_factor=1, vector_factor=8, total_iterations=1200000, cgra_rows=12, cgra_columns=12),
            Kernel(kernel_name="gemm.c", kernel_id=3, arrive_period=3600000, unroll_factor=1, vector_factor=4, total_iterations=1200000, cgra_rows=12, cgra_columns=12),
            Kernel(kernel_name="gemm.c", kernel_id=3, arrive_period=3600000, unroll_factor=1, vector_factor=16, total_iterations=1200000, cgra_rows=12, cgra_columns=12)
            #Kernel(kernel_name="fft.c", kernel_id=4, arrive_period=3840000, unroll_factor=1, vector_factor=8, total_iterations=480000, cgra_rows=4, cgra_columns=4),
            #Kernel(kernel_name="dtw.cpp", kernel_id=5, arrive_period=3932160, unroll_factor=1, vector_factor=8, total_iterations=524288, cgra_rows=4, cgra_columns=4),
             #Kernel(kernel_name="spmv.c", kernel_id=6, arrive_period=4571136, unroll_factor=2, vector_factor=1, total_iterations=507904, cgra_rows=4, cgra_columns=4),
            #Kernel(kernel_name="conv.c", kernel_id=7, arrive_period=1200000, unroll_factor=4, vector_factor=1, total_iterations=400000, cgra_rows=4, cgra_columns=4),
            # Kernel(kernel_name="relu.c", kernel_id=2, arrive_period=4500000, unroll_factor=1, vector_factor=8, total_iterations=1000000, cgra_rows=4, cgra_columns=4),
            # Kernel(kernel_name="histogram.cpp", kernel_id=9, arrive_period=1048576, unroll_factor=1, vector_factor=8, total_iterations=262144, cgra_rows=4, cgra_columns=4),
            #Kernel(kernel_name="mvt.c", kernel_id=0, arrive_period=13500000, unroll_factor=4, vector_factor=1, total_iterations=1800000, cgra_rows=12, cgra_columns=12),
            #Kernel(kernel_name="gemm.c", kernel_id=1, arrive_period=12582912, unroll_factor=2, vector_factor=1, total_iterations=2097152, cgra_rows=4, cgra_columns=4)
            # Kernel(kernel_name="relu+histogram.c", kernel_id=7, arrive_period=3840000, unroll_factor=1, vector_factor=1, total_iterations=480000, cgra_rows=4, cgra_columns=4),
            # Kernel(kernel_name="relu+histogram.c", kernel_id=7, arrive_period=3840000, unroll_factor=2, vector_factor=1, total_iterations=480000, cgra_rows=4, cgra_columns=4),
            #Kernel(kernel_name="relu+histogram.c", kernel_id=7, arrive_period=3840000, unroll_factor=4, vector_factor=1, total_iterations=480000, cgra_rows=12, cgra_columns=12)
            # Kernel(kernel_name="relu+histogram.c", kernel_id=7, arrive_period=3840000, unroll_factor=1, vector_factor=16, total_iterations=480000, cgra_rows=4, cgra_columns=4),
            # Kernel(kernel_name="relu+histogram.c", kernel_id=7, arrive_period=3840000, unroll_factor=1, vector_factor=4, total_iterations=480000, cgra_rows=4, cgra_columns=4),
            # Kernel(kernel_name="relu+histogram.c", kernel_id=7, arrive_period=3840000, unroll_factor=1, vector_factor=8, total_iterations=480000, cgra_rows=4, cgra_columns=4),
            # Kernel(kernel_name="relu+histogram.c", kernel_id=7, arrive_period=3840000, unroll_factor=1, vector_factor=1, total_iterations=480000, cgra_rows=12, cgra_columns=12)
        ]
    ]

    taskCase1=[
        [
            # Kernel(kernel_name="spmv+conv.c", kernel_id=7, arrive_period=3840000, unroll_factor=1, vector_factor=1, total_iterations=480000, cgra_rows=12, cgra_columns=12),
            # Kernel(kernel_name="spmv+conv.c", kernel_id=7, arrive_period=3840000, unroll_factor=1, vector_factor=1, total_iterations=480000, cgra_rows=4, cgra_columns=4),
            # Kernel(kernel_name="fft.c", kernel_id=4, arrive_period=3840000, unroll_factor=1, vector_factor=1, total_iterations=480000, cgra_rows=4, cgra_columns=4),
            # Kernel(kernel_name="dtw.cpp", kernel_id=5, arrive_period=3932160, unroll_factor=1, vector_factor=1, total_iterations=524288, cgra_rows=4, cgra_columns=4)
        ]
    ]
    # taskCase1 = [
    #     [
    #         Kernel(kernel_name="fir.cpp", kernel_id=8, arrive_period=600000, unroll_factor=2, vector_factor=1, total_iterations=300000, cgra_rows=4, cgra_columns=4),
    #         Kernel(kernel_name="latnrm.c", kernel_id=3, arrive_period=3600000, unroll_factor=1, vector_factor=1, total_iterations=1200000, cgra_rows=4, cgra_columns=4),
    #         Kernel(kernel_name="fft.c", kernel_id=4, arrive_period=3840000, unroll_factor=1, vector_factor=8, total_iterations=480000, cgra_rows=4, cgra_columns=4),
    #         Kernel(kernel_name="dtw.cpp", kernel_id=5, arrive_period=3932160, unroll_factor=1, vector_factor=2, total_iterations=524288, cgra_rows=4, cgra_columns=4),
    #         Kernel(kernel_name="spmv.c", kernel_id=6, arrive_period=4571136, unroll_factor=1, vector_factor=4, tot1al_iterations=400000, cgra_rows=4, cgra_columns=4),
    #         Kernel(kernel_name="relu.c", kernel_id=2, arrive_period=4500000, unroll_factor=2, vector_factor=1, total_iterations=1000000, cgra_rows=4, cgra_columns=4),
    #         Kernel(kernel_name="histogram.cpp", kernel_id=9, arrive_period=1048576, unroll_factor=4, vector_factor=1, total_iterations=262144, cgra_rows=4, cgra_columns=4),
    #         Kernel(kernel_name="mvt.c", kernel_id=0, arrive_period=13500000, unroll_factor=1, vector_factor=4, total_iterations=1800000, cgra_rows=4, cgra_columns=4),
    #         Kernel(kernel_name="gemm.c", kernel_id=1, arrive_period=12582912, unroll_factor=1, vector_factor=8, total_iterations=2097152, cgra_rows=4, cgra_columns=4),
    #     ]
    # ]


    # TODO: 尽量让排序id 靠前的kernel 向量化
    # TODO：明确 kernel_id 是通过 static execution time 排序， static execution time 越大，id 越小
    #run_multiple_simulations_and_save_to_csv(baselineCase1, "Baseline", priority_boosting = False, num_cgras=1)  # one cgra is 12x12
    # run_multiple_simulations_and_save_to_csv(taskCase1, "NoBosting", priority_boosting = False, num_cgras=9) # one cgra is 4x4
    run_multiple_simulations_and_save_to_csv(baselineCase1, "Bosting", priority_boosting = 2, num_cgras=9)    # one cgra is 4x4
