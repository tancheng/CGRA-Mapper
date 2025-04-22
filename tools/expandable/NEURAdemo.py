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

# ----------------------------------------------------------------------------
#   global variables                                                        /
# ----------------------------------------------------------------------------

TEST_BENCHS = ["fir.cpp", "latnrm.c", "fft.c", "dtw.cpp", "spmv.c", "conv.c", "relu.c", "histogram.cpp", "mvt.c", "gemm.c"]
TEST_BENCHS_NUM = len(TEST_BENCHS)
DICT_CSV = {'kernels': "", 'DFG nodes': "", 'DFG edges': "", 'recMII': "", 'mappingII': "", 'expandableII': ""}  # column names of generated CSV
DICT_COLUMN = len(DICT_CSV)
JSON_NAME = "./param.json"   # name of generated json file
TIME_OUT_SET = 180

DO_MAPPING = True



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
        self.ii_1 = None  # II when using 1 CGRA, actual II
        self.ii_2 = None  # II when using 2 CGRAs, expandable II
        self.total_iterations = math.ceil(total_iterations / (self.unroll_factor*self.vector_factor)) 
        self.rows = cgra_rows
        self.columns = cgra_columns
        if DO_MAPPING:
            self.get_ii()  # Perform mapping and populate attributes
        else:
            self.read_ii()  # Read from existing csv
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
            compile_command = f"clang-12 -emit-llvm -fno-unroll-loops -fno-vectorize -O3 -o kernel.bc -c ../../test/kernels/{file_source}/{self.kernel_name}"
        elif self.unroll_factor == 1 and self.vector_factor != 1:
            compile_command = f"clang-12 -emit-llvm -fno-unroll-loops -O3 -mllvm -force-vector-width={self.vector_factor} -o kernel.bc -c ../../test/kernels/{file_source}/{self.kernel_name}"
        elif self.unroll_factor != 1 and self.vector_factor == 1:
            compile_command = f"clang-12 -emit-llvm -funroll-loops -mllvm -unroll-count={self.unroll_factor} -fno-vectorize -O3 -o kernel.bc -c ../../test/kernels/{file_source}/{self.kernel_name}"
        else:
            print("Error, invalid unroll and vector factor combination.")
            return            

        compile_proc = subprocess.Popen([compile_command, '-u'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        (compile_out, compile_err) = compile_proc.communicate()

        disassemble_command = "llvm-dis-12 kernel.bc -o ./kernel.ll"
        disassemble_proc = subprocess.Popen([disassemble_command, '-u'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        (disassemble_out, disassemble_err) = disassemble_proc.communicate()


        if compile_err:
            print(f"Compile warning message for {self.kernel_name}: {compile_err}")
        if disassemble_err:
            print(f"Disassemble error message for {self.kernel_name}: {disassemble_err}")
            return

        # collect the potentially targeting kernel/function from kernel.ll
        ir_file = open('kernel.ll', 'r')
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
        get_map_command = "opt-12 -load ../../build/src/libmapperPass.so -mapperPass kernel.bc"
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
                            self.ii_1 = int(output_line.split("[Mapping II: ")[1].split("]")[0])
                            dataS.append(self.ii_1)
                        if "[ExpandableII: " in output_line:
                            self.ii_2 = int(output_line.split("[ExpandableII: ")[1].split("]")[0])
                            dataS.append(self.ii_2)
        
        except eventlet.timeout.Timeout:
            dataS = [0]*(DICT_COLUMN)
            print("Skipping a specific config for kernel: ", self.kernel_name, "Because it runs more than", TIME_OUT_SET/60 , "minute(s).")
        
        if len(dataS) != DICT_COLUMN:
            dataS.extend([0]*(DICT_COLUMN-len(dataS)))

        print(dataS)
        self.df.loc[len(self.df.index)] = dataS

    def map_kernel_skip(self):
        """
        This is a func gain DFG information only without mapping.

        Returns: NULL
        """
        get_map_command = "opt-12 -load ../../build/src/libmapperPass.so -mapperPass kernel.bc"
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

        print(dataS)
        self.df.loc[len(self.df.index)] = dataS

    def get_ii(self):
        """
        This is a func to compile, run and map kernels under sora_json and store the mapping result in csv

        Returns: name of the csv that collects information of mapped kernels 
        """
        csv_name = f'./tmp/t_{self.kernel_name}_{self.rows}x{self.columns}_unroll{self.unroll_factor}_vector{self.vector_factor}.csv'
        print("Generating", csv_name)
        target_kernel = self.comp_kernel()

        sora_json = {
            "kernel": target_kernel,
            "targetFunction": False,
            "targetNested": False,
            "targetLoopsID": [0],
            "doCGRAMapping": DO_MAPPING,
            "row": self.rows,
            "column": self.columns,
            "precisionAware": False,
            "heterogeneity": True,
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
                                        "div" : [0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15]
                                    }
        }

        json_object = json.dumps(sora_json, indent=4)

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
            self.ii_1 = int(df['mappingII'].iloc[1])   # the first data line
            print(self.ii_1)
            self.ii_2 = int(df['expandableII'].iloc[1])    # the first data line
            print(self.ii_2)
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
            return self.ii_1
        elif num_cgras == 2:
            return self.ii_2
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
        self.pure_execution_time = 0  # Track pure execution time for this instance
        self.pure_waiting_time = 0  # Track pure waiting time for this instance
        # Determine the maximum number of CGRAs that can be allocated
        self.max_allocate_cgra = 9

    def __lt__(self, other):
        """
        Compare two KernelInstance instances by arrival time.
        """
        return self.arrival_time < other.arrival_time

    def calculate_execution_time(self):
        """
        Calculate the execution time based on the number of allocated CGRAs 
        at the beginning running time of current kernel. It may change after.

        Returns:
            int: Total execution time in cycles.
        """
        # if self.vector_factor = 8, then when allocate_cgra <= 2, self.ii = ii_1, when 2 < allocate_cgra <= 4, self.ii = ii_2
        if self.kernel.vector_factor == 8:
            if self.allocated_cgras == 1:
                # cgra tile only support vector = 4
                # TODO: self.kernel.ii_1/2
                self.ii = self.kernel.ii_1
            elif self.allocated_cgras == 2:
                self.ii = self.kernel.ii_1
            else:
                # TODO: self.kernel.ii_3/2
                self.ii = self.kernel.ii_2
        else:
            if self.allocated_cgras == 1:
                self.ii = self.kernel.ii_1
            elif self.allocated_cgras == 2:
                self.ii = self.kernel.ii_2
            else:
                raise ValueError(f"Number of CGRAs must be between 1 and {self.max_allocate_cgra}.")
        execution_time = self.kernel.total_iterations * self.ii
        print(f"Calculated execution time for {self.kernel.kernel_name}: {execution_time} cycles (II={self.ii}, iterations={self.kernel.total_iterations})")
        return execution_time
    
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
        new_instance.pure_execution_time = self.pure_execution_time
        new_instance.pure_waiting_time = self.pure_waiting_time
        new_instance.max_allocate_cgra = self.max_allocate_cgra
        return new_instance


# ----------------------------------------------------------------------------
#   function defination                                                      /
# ----------------------------------------------------------------------------

def allocate(instance, current_time, available_cgras, events, running_instances, runned_kernel_names, total_cgra_runtime):
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
    allocate_cgras = min(instance.max_allocate_cgra, available_cgras)
    available_cgras -= allocate_cgras
    instance.start_time = current_time
    instance.allocated_cgras = allocate_cgras
    execution_time = instance.calculate_execution_time()
    instance.end_time = current_time + execution_time
    instance.pure_waiting_time = instance.start_time - instance.arrival_time  # Record pure waiting time
    print(f"Allocated {allocate_cgras} CGRAs to {instance.kernel.kernel_name} at time {current_time}. Execution will end at {instance.end_time}")
    heapq.heappush(events, (instance.end_time, 'end', instance, instance))
    running_instances.append(instance)
    total_cgra_runtime += allocate_cgras * execution_time
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
    instance.pure_execution_time = instance.end_time - instance.start_time  # Record pure execution time
    kernel_latency[instance.kernel.kernel_name] += latency
    print(f"Released {instance.allocated_cgras} CGRAs from {instance.kernel.kernel_name} at time {current_time}. Latency added: {latency} cycles")
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
    if instance.allocated_cgras < instance.max_allocate_cgra and available_cgras > 0:
        possible_alloc = min(instance.max_allocate_cgra - instance.allocated_cgras, available_cgras)
        # Update allocation
        instance.allocated_cgras += possible_alloc
        available_cgras -= possible_alloc
        # Recalculate remaining iterations
        elapsed_time = current_time - instance.start_time
        completed_iters = elapsed_time // instance.ii
        remaining_iters = instance.kernel.total_iterations - completed_iters
        # Update II
        if instance.allocated_cgras == 1:
            instance.ii = instance.kernel.ii_1
        elif instance.allocated_cgras in [2, 3, 4]:
            instance.ii = instance.kernel.ii_2
        new_execution_time = remaining_iters * instance.ii
        # Schedule new end event
        new_end_time = current_time + new_execution_time
        instance.end_time = new_end_time
        print(f"Re-allocated {possible_alloc} CGRAs to {instance.kernel.kernel_name} at time {current_time}. New end time: {new_end_time}")
        # Create a new valid instance for the new end event
        new_instance = instance.copy_with_valid()  # Assume there is a copy method in KernelInstance class
        heapq.heappush(events, (new_end_time, 'end', new_instance, new_instance))
        instance.is_valid = False   # Old instance is invalid
        total_cgra_runtime += possible_alloc * new_execution_time
        # Invalidate old end event by leaving it in the heap but ignoring when processed
    else:
        print(f"Re-allocated CGRAs to {instance.kernel.kernel_name} at time {current_time} Failed.")
    return available_cgras, total_cgra_runtime


def simulate(num_cgras, kernels, priority_bosting, lcm_time=80000000):
    """
    Simulate the execution of multiple kernels on a CGRA architecture.

    Parameters:
        num_cgras (int): The number of CGRAs in the CGRA architecture.
        kernels (list of Kernel): The list of kernels to simulate.
        priority_bosting (bool): Whether to enable priority boosting.
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
    # Dictionary to store per-kernel execution time distribution
    kernel_execution_distribution = {kernel.kernel_name: [] for kernel in kernels}
    # Dictionary to store per-kernel waiting time distribution
    kernel_waiting_distribution = {kernel.kernel_name: [] for kernel in kernels}
    # Dictionary to store per-kernel ratio (iterations per cycle)
    kernel_execution_ratio = {kernel.kernel_name: 0 for kernel in kernels}
    # Dictionary to store per-kernel ratio (iterations per cycle)
    kernel_waiting_ratio = {kernel.kernel_name: 0 for kernel in kernels}
    total_cgra_runtime = 0
    arrive_times_list = {"fir.cpp": 12, "latnrm.c":4, "fft.c":10, "dtw.cpp":7, "spmv.c":6, "conv.c":8, "relu.c":5, "mvt.c":12, "gemm.c":2, "histogram.cpp":2}

    if priority_bosting:
        print("\033[91mpriority_bosting is on\033[0m")

    for kernel in kernels:
        print(f"Kernel {kernel.kernel_name} II_1={kernel.ii_1}, II_2={kernel.ii_2}, total_iterations={kernel.total_iterations}")

    # Schedule initial arrivals for all kernels
    for kernel in kernels:
        first_arrival = 0
        # heapq keeps a priority queue that contains (event_arrive_end_time (int), event_type (str), Kernel, KernelInstance (needed when 'end'))
        heapq.heappush(events, (first_arrival, 'arrival', kernel, None))

    while events:
        event_time, event_type, kernel_or_instance, _ = heapq.heappop(events)
        current_time = event_time
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
                available_cgras, total_cgra_runtime = allocate(instance, current_time, available_cgras, events, running_instances, runned_kernel_names, total_cgra_runtime)
            else:
                waiting_instances.append(instance)
                print(f"No available CGRAs for {kernel.kernel_name}. Added to waiting queue.")

        elif event_type == 'end':
            instance = kernel_or_instance
            if not instance.is_valid:
                # If instance is invalid, means it is re_allocated.
                print(f"Ignoring invalid end event for {instance.kernel.kernel_name}")
                continue
            # Release CGRAs
            available_cgras, total_cgra_runtime = release(instance, current_time, available_cgras, running_instances, completed_instances,kernel_latency, total_cgra_runtime)

            # Update execution time distribution
            kernel_execution_distribution[instance.kernel.kernel_name].append(instance.pure_execution_time)
            kernel_waiting_distribution[instance.kernel.kernel_name].append(instance.pure_waiting_time)

            # Check waiting queue
            while waiting_instances and available_cgras >= 1:
                instance = waiting_instances.pop(0)
                print(f"Allocating CGRAs to waiting instance {instance.kernel.kernel_name}")
                available_cgras, total_cgra_runtime = allocate(instance, current_time, available_cgras, events, running_instances, runned_kernel_names, total_cgra_runtime)

            # Check running instances for possible re-allocation
            if priority_bosting:
                for running in running_instances:
                    available_cgras, total_cgra_runtime = re_allocate(running, current_time, available_cgras, events, total_cgra_runtime)

    # Calculate ratio for each kernel
    for kernel in kernels:
        total_execution_time = sum(
            [inst.pure_execution_time for inst in completed_instances if inst.kernel.kernel_name == kernel.kernel_name])
        total_waiting_time = sum(
            [inst.pure_waiting_time for inst in completed_instances if inst.kernel.kernel_name == kernel.kernel_name])
        total_time = total_execution_time + total_waiting_time
        kernel_execution_ratio[kernel.kernel_name] = total_execution_time / total_time if total_time > 0 else 0
        kernel_waiting_ratio[kernel.kernel_name] = total_waiting_time / total_time if total_time > 0 else 0

    # Calculate utilization of total CGRAs
    cgra_utilization = total_cgra_runtime / (current_time * num_cgras)
    overall_latency = current_time  # when all kernels are done

    print(f"Simulation completed. Kernel latencies: {kernel_latency}")
    print(f"Kernel execution_ratio: {kernel_execution_ratio}")
    print(f"Kernel execution time distributions: {kernel_execution_distribution}")
    print(f"Kernel Runned List: {runned_kernel_names}")
    print(f"CGRA utilization: {cgra_utilization}")
    print(f"overall latency: {overall_latency}")
    return kernel_latency, kernel_waiting_distribution, kernel_execution_ratio, kernel_waiting_ratio, kernel_execution_distribution, cgra_utilization, overall_latency


def run_multiple_simulations_and_save_to_csv(kernels_list, csvname, priority_bosting, num_cgras=9):
    """
    Run multiple simulations and save the results to a CSV file.

    Parameters:
        kernels_list (list of list of Kernel): A list of kernels.
        csvname (str): The name of the CSV file.
        priority_bosting (bool): Whether to enable priority boosting.
        num_cgras (int): The number of CGRAs, default 9.
    """
    for i, kernels in enumerate(kernels_list, start=1):
        kernel_latency, kernel_waiting_distribution, kernel_execution_ratio, kernel_waiting_ratio, kernel_execution_distribution, cgra_utilization, overall_latency = simulate(num_cgras, kernels, priority_bosting)

        # Calculate fastest, slowest, and average execution time per kernel
        execution_stats = {}
        for kernel_name, execution_times in kernel_execution_distribution.items():
            if execution_times:
                fastest = min(execution_times)
                slowest = max(execution_times)
                average = sum(execution_times) / len(execution_times)
                total = sum(execution_times)
                execution_stats[kernel_name] = {
                    "fastest_execution_time": fastest,
                    "slowest_execution_time": slowest,
                    "average_execution_time": average,
                    "total_execution_time": total
                }

        # Calculate fastest, slowest, and average waiting time per kernel
        waiting_stats = {}
        for kernel_name, waiting_times in kernel_waiting_distribution.items():
            if waiting_times:
                fastest = min(waiting_times)
                slowest = max(waiting_times)
                average = sum(waiting_times) / len(waiting_times)
                total = sum(waiting_times)
                waiting_stats[kernel_name] = {
                    "fastest_waiting_time": fastest,
                    "slowest_waiting_time": slowest,
                    "average_waiting_time": average,
                    "total_waiting_time": total
                }

        all_results = []
        for kernel in kernels:
            kernel_name = kernel.kernel_name
            result = {
                "Kernel_Name": kernel_name,
                "Arrive_Period": kernel.arrive_period,
                "Unroll_Factor": kernel.unroll_factor,
                "Vector_Factor": kernel.vector_factor,
                "fastest_execution_time": execution_stats.get(kernel_name, {}).get("fastest_execution_time", None),
                "slowest_execution_time": execution_stats.get(kernel_name, {}).get("slowest_execution_time", None),
                "Average_Execution_Time": execution_stats.get(kernel_name, {}).get("average_execution_time", None),
                "fastest_waiting_time": waiting_stats.get(kernel_name, {}).get("fastest_waiting_time", None),
                "slowest_waiting_time": waiting_stats.get(kernel_name, {}).get("slowest_waiting_time", None),
                "Average_Waiting_Time": waiting_stats.get(kernel_name, {}).get("average_waiting_time", None),
                "Total_Execution_Time": execution_stats.get(kernel_name, {}).get("total_execution_time", None),
                "Total_Waiting_Time": waiting_stats.get(kernel_name, {}).get("total_waiting_time", None),
                "Execution_Time Ratio": kernel_execution_ratio[kernel_name],
                "Waiting_Time Ratio": kernel_waiting_ratio[kernel_name],
                "Overall_Case_Latency": overall_latency,
                "CGRA Utilization": cgra_utilization,
                "Total_Execution_Time Ratio": (execution_stats.get(kernel_name, {}).get("total_execution_time", None))/overall_latency,
                "Total_Waiting_Time Ratio": (waiting_stats.get(kernel_name, {}).get("total_waiting_time", None))/overall_latency,
                "Total_Latency Ratio":  (execution_stats.get(kernel_name, {}).get("total_execution_time", None) + waiting_stats.get(kernel_name, {}).get("total_waiting_time", None))/overall_latency
            }
            all_results.append(result)


        df = pd.DataFrame(all_results)
        file_name = f'simulation_{csvname}_case{i}.csv'
        df.to_csv(file_name, index=False)


if __name__ == "__main__":
    baselineCase1=[
        [
            Kernel(kernel_name="fir.cpp", kernel_id =0, arrive_period =1500000, unroll_factor =1,vector_factor =1, total_iterations =300000, cgra_rows= 12, cgra_columns=12) ,
            Kernel(kernel_name="conv.c", kernel_id =5, arrive_period =2500000, unroll_factor =1,vector_factor =1, total_iterations =400000, cgra_rows= 12, cgra_columns=12) ,
            Kernel(kernel_name="relu.c", kernel_id =6, arrive_period =4000000, unroll_factor =1,vector_factor =1, total_iterations =1000000, cgra_rows= 12, cgra_columns=12) ,
            Kernel(kernel_name="histogram.cpp", kernel_id =7, arrive_period =1200000, unroll_factor =1,vector_factor =1, total_iterations =262144, cgra_rows= 12, cgra_columns=12) ,
        ]
    ]
    taskCase1 = [
        [
            Kernel(kernel_name="fir.cpp", kernel_id =0, arrive_period =300000, unroll_factor =1,vector_factor =8, total_iterations =300000, cgra_rows= 4, cgra_columns=4) ,
            Kernel(kernel_name="conv.c", kernel_id =5, arrive_period =400000, unroll_factor =1,vector_factor =8, total_iterations =400000, cgra_rows= 4, cgra_columns=4) ,
            Kernel(kernel_name="relu.c", kernel_id =6, arrive_period =1000000, unroll_factor =1,vector_factor =8, total_iterations =1000000, cgra_rows= 4, cgra_columns=4) ,
            Kernel(kernel_name="histogram.cpp", kernel_id =7, arrive_period =262144, unroll_factor =1,vector_factor =8, total_iterations =262144, cgra_rows= 4, cgra_columns=4) ,
        ]
    ]
    run_multiple_simulations_and_save_to_csv(baselineCase1, "Baseline", priority_bosting = True, num_cgras=1)  # one cgra is 4x4
    run_multiple_simulations_and_save_to_csv(taskCase1, "NoBosting", priority_bosting = False, num_cgras=9)  
    run_multiple_simulations_and_save_to_csv(taskCase1, "Bosting", priority_bosting = True, num_cgras=9)  
