# ----------------------------------------------------------------------------
#   Filename: main.py                                                   /
#   Description: simulate multi-kernel running on multi-CGRA                /
#   Author: Miaomiao Jiang, start from 2025-02-24                           /
# ----------------------------------------------------------------------------

import argparse
import core
import json
import os
from pathlib import Path
# from .visualization import generate_schedule_figure, generate_gantt_chart


# ----------------------------------------------------------------------------
#   global variables                                                        /
# ----------------------------------------------------------------------------
JSON_NAME = "./param.json"   # name of generated json file
KERNEL_DIRECTORY = "../../test/kernels"
VECTOR_LANE = 2
DO_MAPPING = False
TIME_OUT_SET = 300
VISUALIZATION = False
CGRA_CONFIG = 4
# ========== Configuration Section ==========
# Static kernel data (name: (sort_id, total_iterations, static_execution_time))
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

# Case configuration dictionary (task_id: [A_P, UNROLL_FACTORS, VECTOR_FACTORS])
TASK_CONFIGS = {
    1: {
        'A_P': [81920, 81920, 81920, 327680, 327680, 1638400, 81920, 1638400, 81920],
        'UNROLL_FACTORS': [1]*9,
        'VECTOR_FACTORS': [1]*9
    },
    2: {
        'A_P': [102400, 102400, 102400, 327680, 327680, 1638400, 163840, 1638400, 81920],
        'UNROLL_FACTORS': [1,2,2,1,2,2,2,1,2],
        'VECTOR_FACTORS': [4, 1, 1, 4, 1, 1, 1, 4, 1]
    },
    3: {
        'A_P': [102400, 102400, 102400, 409600, 409600, 2621440, 102400, 2621440, 81920],
        'UNROLL_FACTORS': [1,4,2,1,4,4,4,1,4],
        'VECTOR_FACTORS': [8, 1, 1, 8, 1, 1, 1, 8, 1]
    },
    4: {
        'A_P': [163840, 163840, 163840, 655360, 655360, 3276800, 163840, 3276800, 163840],
        'UNROLL_FACTORS': [1,4,1,2,4,4,4,1,4],
        'VECTOR_FACTORS': [16, 1, 1, 16, 1, 1, 1, 16, 1]
    },
    5: {
        'A_P': [204800, 204800, 204800, 819200, 819200, 5242880, 204800, 5242880, 204800],
        'UNROLL_FACTORS': [1,4,1,1,4,4,4,1,4],
        'VECTOR_FACTORS': [16, 1, 16, 16, 1, 1, 1, 16, 1]
    },
    6: {
        'A_P': [327680, 327680, 327680, 819200, 819200, 6553600, 204800, 5242880, 204800],
        'UNROLL_FACTORS': [1,4,1,1,4,4,4,1,4],
        'VECTOR_FACTORS': [16, 1, 16, 16, 1, 1, 1, 16, 1]
    }
}

def str_to_bool(value):
    if isinstance(value, bool):
        return value
    if str(value).lower() in ('yes', 'true', 't', 'y', '1'):
        return True
    elif str(value).lower() in ('no', 'false', 'f', 'n', '0'):
        return False
    raise argparse.ArgumentTypeError('Invalid boolean value (accepted: 0/1, true/false, yes/no)')


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='Multi-CGRA Task Scheduling Tool'
    )
    # Core application arguments
    parser.add_argument('--cgra-config', type=int, default=CGRA_CONFIG,
                       help='Path to CGRA configuration file')
    parser.add_argument('--json-name', type=str, default=JSON_NAME,
                       help='JSON configuration file name')
    parser.add_argument('--kernel-directory', type=str, default=KERNEL_DIRECTORY,
                       help='Kernel directory path')
    parser.add_argument('--vector-lane', type=int, default=VECTOR_LANE,
                       help='Vector lane configuration')
    parser.add_argument('--do-mapping', type=str_to_bool, default=DO_MAPPING,
                       help='Enable/disable mapping phase [y/n]')
    parser.add_argument('--time-out-set', type=int, default=TIME_OUT_SET,
                       help='Timeout setting for operations')
    parser.add_argument('--visualize', type=str_to_bool, default=VISUALIZATION,
                       help='Generate visualization figures [y/n]')

    return parser.parse_args()


def load_configuration():
    """Load and merge configurations from multiple sources with priority:
    1. Command line arguments (highest priority)
    2. Default values (lowest priority)
    """
    global JSON_NAME, KERNEL_DIRECTORY, VECTOR_LANE, DO_MAPPING, TIME_OUT_SET, VISUALIZATION, CGRA_CONFIG

    # Parse command line arguments
    args = parse_arguments()

    # Update global configuration with command line arguments
    JSON_NAME = args.json_name
    KERNEL_DIRECTORY = args.kernel_directory
    VECTOR_LANE = args.vector_lane
    DO_MAPPING = args.do_mapping
    TIME_OUT_SET = args.time_out_set
    VISUALIZATION = args.visualize
    CGRA_CONFIG = args.cgra_config


# ========== Task Loading Function ==========
def load_tasks(task_id, task_type="baseline"):
    """
    Load task list based on task_id and CGRA type

    Args:
        task_id: Configuration case ID
        task_type: "baseline" or "task", corresponding to 12x12 and 4x4 CGRA respectively

    Returns:
        task_list: List of task objects
    """
    if task_id not in TASK_CONFIGS:
        raise ValueError(f"Task{task_id} configuration does not exist")

    config = TASK_CONFIGS[task_id]
    A_P = config['A_P']
    UNROLL_FACTORS = config['UNROLL_FACTORS']
    VECTOR_FACTORS = config['VECTOR_FACTORS']

    # Validate parameter lengths
    lists = [KERNEL_DATA, A_P, UNROLL_FACTORS, VECTOR_FACTORS]
    if len(set(len(lst) for lst in lists if lst)) > 1:
        raise ValueError(f"Task{task_id} parameter length mismatch: {[len(lst) for lst in lists]}")

    # Set CGRA dimensions
    if task_type == "baseline":
        cgra_rows, cgra_columns = 12, 12
    elif task_type == "task":
        cgra_rows, cgra_columns = 4, 4
    else:
        raise ValueError("task_type must be either 'baseline' or 'task'")

    # Generate task list
    task_list = []
    for i, (kernel_name, (kernel_id, total_iters, _)) in enumerate(KERNEL_DATA.items()):
        task = core.Kernel(
            kernel_name=kernel_name,
            kernel_id=kernel_id,
            arrive_period=A_P[i] if A_P else 0,
            unroll_factor=UNROLL_FACTORS[i],
            vector_factor=VECTOR_FACTORS[i],
            total_iterations=total_iters,
            cgra_rows=cgra_rows,
            cgra_columns=cgra_columns
        )
        task_list.append(task)

    return task_list


def run_simulation_for_case(task_id, num_task_cgras = 9, file_name = "NULL", load_from_file = False):
    """
    Complete simulation workflow for specified case

    Args:
        task_id: Configuration case ID to run simulation for
    """
    print(f"[Step 1] Loading tasks for task {task_id}...")

    if load_from_file:
        # Load baseline tasks (12x12 CGRA)
        baseline_tasks = load_tasks_from_file(f"{file_name}baseline.json")
        # Load task tasks (4x4 CGRA)
        task_tasks = load_tasks_from_file(f"{file_name}task.json")
    else:
        # Load baseline tasks (12x12 CGRA)
        baseline_tasks = load_tasks(task_id, "baseline")
        # Load task tasks (4x4 CGRA)
        task_tasks = load_tasks(task_id, "task")

    # Run baseline simulation
    core.run_multiple_simulations_and_save_to_csv(
        baseline_tasks,
        "Baseline",
        priority_boosting=0,
        kernel_case=task_id,
        num_cgras=1  # one cgra is 12x12
    )

    # Run task simulation
    core.run_multiple_simulations_and_save_to_csv(
        task_tasks,
        "NoBoosting",
        priority_boosting=0,
        kernel_case=task_id,
        num_cgras=num_task_cgras  # 9 of 4x4 CGRAs
    )
    core.run_multiple_simulations_and_save_to_csv(
        task_tasks,
        "BoostingScalar",
        priority_boosting=1,
        kernel_case=task_id,
        num_cgras=num_task_cgras  # 9 of 4x4 CGRAs
    )
    core.run_multiple_simulations_and_save_to_csv(
        task_tasks,
        "BoostingScalarFuse",
        priority_boosting=2,
        kernel_case=task_id,
        num_cgras=num_task_cgras  # 9 of 4x4 CGRAs
    )
    core.run_multiple_simulations_and_save_to_csv(
        task_tasks,
        "BoostingScalarFuseVector",
        priority_boosting=3,
        kernel_case=task_id,
        num_cgras=num_task_cgras  # 9 of 4x4 CGRAs
    )



def load_tasks_from_file(filename):
    """
    Load task list from JSON file

    Args:
        filename: Input JSON filename

    Returns:
        task_list: List of reconstructed task objects
    """
    if not os.path.exists(filename):
        raise FileNotFoundError(f"Task file {filename} not found")

    with open(filename, 'r') as f:
        tasks_data = json.load(f)

    # Reconstruct task objects from dictionaries
    task_list = []
    for task_dict in tasks_data:
        task = core.Kernel(
            kernel_name=task_dict['kernel_name'],
            kernel_id=task_dict['kernel_id'],
            arrive_period=task_dict['arrive_period'],
            unroll_factor=task_dict['unroll_factor'],
            vector_factor=task_dict['vector_factor'],
            total_iterations=task_dict['total_iterations'],
            cgra_rows=task_dict['cgra_rows'],
            cgra_columns=task_dict['cgra_columns']
        )
        task_list.append(task)

    print(f"Tasks loaded from {filename}")
    return task_list



def main():
    """Main workflow control function"""
    # 1. Load configuration (includes parsing arguments)
    load_configuration()

    print("=== Multi-CGRA Task Scheduling Tool ===")
    print(f"CGRA Config: {CGRA_CONFIG}")
    print(f"Vector Lane: {VECTOR_LANE}")
    print(f"Do Mapping: {DO_MAPPING}")
    print(f"Timeout: {TIME_OUT_SET}")

    # 2. Create output directory
    print(f"Intermediate reslut in: ./tmp")
    output_dir = Path("./tmp")
    output_dir.mkdir(parents=True, exist_ok=True)

    # 3. Load tasks and configuration
    print("[Step 1] Loading tasks and CGRA configuration...")
    # tasks = load_tasks(JSON_NAME)  # Use global JSON_NAME
    # cgra_config = load_cgra_config(CGRA_CONFIG)

    # 4. Execute scheduling
    print("[Step 2] Scheduling tasks on 4x4 Multi-CGRA...")
    for task_case_id in TASK_CONFIGS:
        run_simulation_for_case(task_case_id)

    # 4. Execute scheduling
    print("[Step 3] Scheduling tasks on 2x2, 3x3, 5x5 Multi-CGRA...")
    run_simulation_for_case(task_case_id = 6, num_task_cgras=4, file_name="2x2", load_from_file=True)  # 2x2
    run_simulation_for_case(task_case_id = 6, num_task_cgras=9, file_name="3x3", load_from_file=True)  # 3x3
    run_simulation_for_case(task_case_id = 6, num_task_cgras=16, file_name="4x4", load_from_file=True)  # 2x2
    run_simulation_for_case(task_case_id = 6, num_task_cgras=25, file_name="5x5", load_from_file=True)  # 2x2

    # 5. Generate visualization
    if VISUALIZATION:  # Use global variable
        print(f"[Step 4] Generating visualization figures...")

        # Generate schedule Gantt chart
        # gantt_file = output_dir / f'schedule_gantt.png'  # Using default format
        # generate_gantt_chart(schedule_results, output_path=gantt_file)
        # print(f"  Generated: {gantt_file}")

        # # Generate resource utilization chart
        # util_file = output_dir / f'resource_utilization.png'
        # generate_schedule_figure(schedule_results, output_path=util_file)
        # print(f"  Generated: {util_file}")

    print("\n=== Scheduling completed successfully! ===")

if __name__ == '__main__':
    main()