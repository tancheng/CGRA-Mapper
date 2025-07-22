import argparse
import NeuraDemo
import NeuraDemoArchive

parser = argparse.ArgumentParser()
parser.add_argument('--old-new',
                    type=int,
                    default=0)
args, _ = parser.parse_known_args()

def generate_and_print_kernel_configs():
    """生成并打印内核配置和到达时间
    """
    # 静态内核数据 (名称: (内核ID, 总迭代次数, 静态执行时间))
    KERNEL_DATA = {
        "fir.cpp": (8, 300000, 600000),
        "latnrm.c": (3, 1200000, 400000),
        "fft.c": (4, 480000, 3342336),
        "dtw.cpp": (5, 524288, 1572864),
        "spmv.c": (6, 507904, 800000),
        "conv.c": (7, 400000, 1200000),
        "relu.c": (2, 1000000, 3000000),
        "histogram.cpp": (9, 262144, 524288),
        "mvt.c": (0, 1800000, 5880000),
        "gemm.c": (1, 2097152, 21120000),
        "spmv+conv.c": (7, 480000, 1200000)
    }

    CGRA_SIZES = [12, 4]  # 按照需求，先生成12的配置，再生成4的配置
    A_P = [1, 1.5, 2, 2.5, 3, 1, 1.5, 2, 2.5, 3, 2]  # 到达周期乘数列表
    UNROLL_FACTORS = [1, 2, 1, 4, 1, 2, 1, 4, 1, 2, 1]  # unroll_factor列表
    VECTOR_FACTORS = [1, 1, 2, 1, 2, 1, 4, 1, 2, 1, 4]  # vector_factor列表

    # 确保所有列表长度一致
    lists = [KERNEL_DATA, A_P, UNROLL_FACTORS, VECTOR_FACTORS]
    if len(set(len(lst) for lst in lists)) != 1:
        raise ValueError(f"参数长度不一致: {[len(lst) for lst in lists]}")

    # 生成baselineCase1 (CGRA_SIZES=12)
    print("baselineCase1=[")
    print("    [")

    for i, (kernel_name, (kernel_id, total_iters, static_exec_time)) in enumerate(KERNEL_DATA.items()):
        # 使用对应索引位置的值
        arrive_period = round(A_P[i] * static_exec_time)
        unroll_factor = UNROLL_FACTORS[i]
        vector_factor = VECTOR_FACTORS[i]

        # 只生成CGRA_SIZES=12的配置
        rows = 12
        print(f'        NeuraDemo.Kernel(kernel_name="{kernel_name}", '
              f'kernel_id={kernel_id}, '
              f'arrive_period={arrive_period}, '
              f'unroll_factor={unroll_factor}, '
              f'vector_factor={vector_factor}, '
              f'total_iterations={total_iters}, '
              f'cgra_rows={rows}, '
              f'cgra_columns={rows}),')

    print("    ]")
    print("]")

    # 生成taskCase1 (CGRA_SIZES=4)
    print("\ntaskCase1=[")
    print("    [")

    for i, (kernel_name, (kernel_id, total_iters, static_exec_time)) in enumerate(KERNEL_DATA.items()):
        # 使用对应索引位置的值
        arrive_period = round(A_P[i] * static_exec_time)
        unroll_factor = UNROLL_FACTORS[i]
        vector_factor = VECTOR_FACTORS[i]

        # 只生成CGRA_SIZES=4的配置
        rows = 4
        print(f'        NeuraDemo.Kernel(kernel_name="{kernel_name}", '
              f'kernel_id={kernel_id}, '
              f'arrive_period={arrive_period}, '
              f'unroll_factor={unroll_factor}, '
              f'vector_factor={vector_factor}, '
              f'total_iterations={total_iters}, '
              f'cgra_rows={rows}, '
              f'cgra_columns={rows}),')

    print("    ]")
    print("]")

# 调用函数生成输出
generate_and_print_kernel_configs()

if args.old_new == 0:
    # NeuraDemoArchive
    baselineCase1=[
        [
            NeuraDemoArchive.Kernel(kernel_name="fir.cpp", kernel_id=8, arrive_period=600000, unroll_factor=1, vector_factor=8, total_iterations=300000, cgra_rows=4, cgra_columns=4),
            NeuraDemoArchive.Kernel(kernel_name="latnrm.c", kernel_id=3, arrive_period=3600000, unroll_factor=1, vector_factor=8, total_iterations=1200000, cgra_rows=4, cgra_columns=4),
            NeuraDemoArchive.Kernel(kernel_name="fft.c", kernel_id=4, arrive_period=3840000, unroll_factor=1, vector_factor=8, total_iterations=480000, cgra_rows=4, cgra_columns=4),
            NeuraDemoArchive.Kernel(kernel_name="dtw.cpp", kernel_id=5, arrive_period=3932160, unroll_factor=1, vector_factor=8, total_iterations=524288, cgra_rows=4, cgra_columns=4),
            NeuraDemoArchive.Kernel(kernel_name="spmv.c", kernel_id=6, arrive_period=4571136, unroll_factor=1, vector_factor=8, total_iterations=507904, cgra_rows=4, cgra_columns=4),
            NeuraDemoArchive.Kernel(kernel_name="conv.c", kernel_id=7, arrive_period=1200000, unroll_factor=1, vector_factor=8, total_iterations=400000, cgra_rows=4, cgra_columns=4),
            NeuraDemoArchive.Kernel(kernel_name="relu.c", kernel_id=2, arrive_period=4500000, unroll_factor=1, vector_factor=8, total_iterations=1000000, cgra_rows=4, cgra_columns=4),
            NeuraDemoArchive.Kernel(kernel_name="histogram.cpp", kernel_id=9, arrive_period=1048576, unroll_factor=1, vector_factor=8, total_iterations=262144, cgra_rows=4, cgra_columns=4),
            NeuraDemoArchive.Kernel(kernel_name="mvt.c", kernel_id=0, arrive_period=13500000, unroll_factor=1, vector_factor=8, total_iterations=1800000, cgra_rows=4, cgra_columns=4),
            NeuraDemoArchive.Kernel(kernel_name="gemm.c", kernel_id=1, arrive_period=12582912, unroll_factor=1, vector_factor=8, total_iterations=2097152, cgra_rows=4, cgra_columns=4),
            #NeuraDemoArchive.Kernel(kernel_name="spmv+conv.c", kernel_id=7, arrive_period=3840000, unroll_factor=1, vector_factor=8, total_iterations=480000, cgra_rows=4, cgra_columns=4)
        ]
    ]

    NeuraDemoArchive.run_multiple_simulations_and_save_to_csv(baselineCase1, "Baseline", priority_bosting = False, num_cgras=1)  # one cgra is 12x12
    # run_multiple_simulations_and_save_to_csv(taskCase1, "NoBosting", priority_bosting = False, num_cgras=9) # one cgra is 4x4
    # run_multiple_simulations_and_save_to_csv(taskCase1, "Bosting", priority_bosting = True, num_cgras=3)    # one cgra is 4x4
elif args.old_new == 1:
    # NeuraDemo
    baselineCase1=[
        [
            NeuraDemo.Kernel(kernel_name="fir.cpp", kernel_id=8, arrive_period=600000, unroll_factor=1, vector_factor=1, total_iterations=300000, cgra_rows=12, cgra_columns=12),
            NeuraDemo.Kernel(kernel_name="latnrm.c", kernel_id=3, arrive_period=3600000, unroll_factor=1, vector_factor=1, total_iterations=1200000, cgra_rows=12, cgra_columns=12),
            NeuraDemo.Kernel(kernel_name="fft.c", kernel_id=4, arrive_period=3840000, unroll_factor=1, vector_factor=1, total_iterations=480000, cgra_rows=12, cgra_columns=12),
            NeuraDemo.Kernel(kernel_name="dtw.cpp", kernel_id=5, arrive_period=3932160, unroll_factor=1, vector_factor=1, total_iterations=524288, cgra_rows=12, cgra_columns=12),
            NeuraDemo.Kernel(kernel_name="spmv.c", kernel_id=6, arrive_period=4571136, unroll_factor=1, vector_factor=1, total_iterations=507904, cgra_rows=12, cgra_columns=12),
            NeuraDemo.Kernel(kernel_name="conv.c", kernel_id=7, arrive_period=1200000, unroll_factor=1, vector_factor=1, total_iterations=400000, cgra_rows=12, cgra_columns=12),
            NeuraDemo.Kernel(kernel_name="relu.c", kernel_id=2, arrive_period=4500000, unroll_factor=1, vector_factor=1, total_iterations=1000000, cgra_rows=12, cgra_columns=12),
            NeuraDemo.Kernel(kernel_name="histogram.cpp", kernel_id=9, arrive_period=1048576, unroll_factor=1, vector_factor=1, total_iterations=262144, cgra_rows=12, cgra_columns=12),
            NeuraDemo.Kernel(kernel_name="mvt.c", kernel_id=0, arrive_period=13500000, unroll_factor=1, vector_factor=1, total_iterations=1800000, cgra_rows=12, cgra_columns=12),
            NeuraDemo.Kernel(kernel_name="gemm.c", kernel_id=1, arrive_period=12582912, unroll_factor=1, vector_factor=1, total_iterations=2097152, cgra_rows=12, cgra_columns=12),
            #NeuraDemo.Kernel(kernel_name="spmv+conv.c", kernel_id=7, arrive_period=3840000, unroll_factor=1, vector_factor=8, total_iterations=480000, cgra_rows=4, cgra_columns=4)
        ]
    ]

    taskCase1=[
        [
            NeuraDemo.Kernel(kernel_name="fir.cpp", kernel_id=8, arrive_period=600000, unroll_factor=1, vector_factor=1, total_iterations=300000, cgra_rows=12, cgra_columns=12),
            NeuraDemo.Kernel(kernel_name="latnrm.c", kernel_id=3, arrive_period=3600000, unroll_factor=1, vector_factor=1, total_iterations=1200000, cgra_rows=12, cgra_columns=12),
            NeuraDemo.Kernel(kernel_name="fft.c", kernel_id=4, arrive_period=3840000, unroll_factor=1, vector_factor=1, total_iterations=480000, cgra_rows=12, cgra_columns=12),
            NeuraDemo.Kernel(kernel_name="dtw.cpp", kernel_id=5, arrive_period=3932160, unroll_factor=1, vector_factor=1, total_iterations=524288, cgra_rows=12, cgra_columns=12),
            NeuraDemo.Kernel(kernel_name="spmv.c", kernel_id=6, arrive_period=4571136, unroll_factor=1, vector_factor=1, total_iterations=507904, cgra_rows=12, cgra_columns=12),
            NeuraDemo.Kernel(kernel_name="conv.c", kernel_id=7, arrive_period=1200000, unroll_factor=1, vector_factor=1, total_iterations=400000, cgra_rows=12, cgra_columns=12),
            NeuraDemo.Kernel(kernel_name="relu.c", kernel_id=2, arrive_period=4500000, unroll_factor=1, vector_factor=1, total_iterations=1000000, cgra_rows=12, cgra_columns=12),
            NeuraDemo.Kernel(kernel_name="histogram.cpp", kernel_id=9, arrive_period=1048576, unroll_factor=1, vector_factor=1, total_iterations=262144, cgra_rows=12, cgra_columns=12),
            NeuraDemo.Kernel(kernel_name="mvt.c", kernel_id=0, arrive_period=13500000, unroll_factor=1, vector_factor=1, total_iterations=1800000, cgra_rows=12, cgra_columns=12),
            NeuraDemo.Kernel(kernel_name="gemm.c", kernel_id=1, arrive_period=12582912, unroll_factor=1, vector_factor=1, total_iterations=2097152, cgra_rows=12, cgra_columns=12),
            #NeuraDemo.Kernel(kernel_name="spmv+conv.c", kernel_id=7, arrive_period=3840000, unroll_factor=1, vector_factor=8, total_iterations=480000, cgra_rows=4, cgra_columns=4)
        ]
    ]

    NeuraDemo.run_multiple_simulations_and_save_to_csv(baselineCase1, "Baseline", priority_bosting = False, num_cgras=1)  # one cgra is 12x12
    # NeuraDemo.run_multiple_simulations_and_save_to_csv(taskCase1, "NoBosting", priority_bosting = False, num_cgras=9) # one cgra is 4x4
    # NeuraDemo.run_multiple_simulations_and_save_to_csv(taskCase1, "Bosting", priority_bosting = True, num_cgras=9)    # one cgra is 4x4

    # NeuraDemo
    baselineCase1=[
        [
            NeuraDemo.Kernel(kernel_name="fir.cpp", kernel_id=8, arrive_period=600000, unroll_factor=1, vector_factor=1, total_iterations=300000, cgra_rows=12, cgra_columns=12),
            NeuraDemo.Kernel(kernel_name="latnrm.c", kernel_id=3, arrive_period=3600000, unroll_factor=1, vector_factor=1, total_iterations=1200000, cgra_rows=12, cgra_columns=12),
            NeuraDemo.Kernel(kernel_name="fft.c", kernel_id=4, arrive_period=3840000, unroll_factor=1, vector_factor=1, total_iterations=480000, cgra_rows=12, cgra_columns=12),
            NeuraDemo.Kernel(kernel_name="dtw.cpp", kernel_id=5, arrive_period=3932160, unroll_factor=1, vector_factor=1, total_iterations=524288, cgra_rows=12, cgra_columns=12),
            NeuraDemo.Kernel(kernel_name="spmv.c", kernel_id=6, arrive_period=4571136, unroll_factor=1, vector_factor=1, total_iterations=507904, cgra_rows=12, cgra_columns=12),
            NeuraDemo.Kernel(kernel_name="conv.c", kernel_id=7, arrive_period=1200000, unroll_factor=1, vector_factor=1, total_iterations=400000, cgra_rows=12, cgra_columns=12),
            NeuraDemo.Kernel(kernel_name="relu.c", kernel_id=2, arrive_period=4500000, unroll_factor=1, vector_factor=1, total_iterations=1000000, cgra_rows=12, cgra_columns=12),
            NeuraDemo.Kernel(kernel_name="histogram.cpp", kernel_id=9, arrive_period=1048576, unroll_factor=1, vector_factor=1, total_iterations=262144, cgra_rows=12, cgra_columns=12),
            NeuraDemo.Kernel(kernel_name="mvt.c", kernel_id=0, arrive_period=13500000, unroll_factor=1, vector_factor=1, total_iterations=1800000, cgra_rows=12, cgra_columns=12),
            NeuraDemo.Kernel(kernel_name="gemm.c", kernel_id=1, arrive_period=12582912, unroll_factor=1, vector_factor=1, total_iterations=2097152, cgra_rows=12, cgra_columns=12),
            #NeuraDemo.Kernel(kernel_name="spmv+conv.c", kernel_id=7, arrive_period=3840000, unroll_factor=1, vector_factor=8, total_iterations=480000, cgra_rows=4, cgra_columns=4)
        ]
    ]

    taskCase1=[
        [
            NeuraDemo.Kernel(kernel_name="fir.cpp", kernel_id=8, arrive_period=600000, unroll_factor=1, vector_factor=1, total_iterations=300000, cgra_rows=12, cgra_columns=12),
            NeuraDemo.Kernel(kernel_name="latnrm.c", kernel_id=3, arrive_period=3600000, unroll_factor=1, vector_factor=1, total_iterations=1200000, cgra_rows=12, cgra_columns=12),
            NeuraDemo.Kernel(kernel_name="fft.c", kernel_id=4, arrive_period=3840000, unroll_factor=1, vector_factor=1, total_iterations=480000, cgra_rows=12, cgra_columns=12),
            NeuraDemo.Kernel(kernel_name="dtw.cpp", kernel_id=5, arrive_period=3932160, unroll_factor=1, vector_factor=1, total_iterations=524288, cgra_rows=12, cgra_columns=12),
            NeuraDemo.Kernel(kernel_name="spmv.c", kernel_id=6, arrive_period=4571136, unroll_factor=1, vector_factor=1, total_iterations=507904, cgra_rows=12, cgra_columns=12),
            NeuraDemo.Kernel(kernel_name="conv.c", kernel_id=7, arrive_period=1200000, unroll_factor=1, vector_factor=1, total_iterations=400000, cgra_rows=12, cgra_columns=12),
            NeuraDemo.Kernel(kernel_name="relu.c", kernel_id=2, arrive_period=4500000, unroll_factor=1, vector_factor=1, total_iterations=1000000, cgra_rows=12, cgra_columns=12),
            NeuraDemo.Kernel(kernel_name="histogram.cpp", kernel_id=9, arrive_period=1048576, unroll_factor=1, vector_factor=1, total_iterations=262144, cgra_rows=12, cgra_columns=12),
            NeuraDemo.Kernel(kernel_name="mvt.c", kernel_id=0, arrive_period=13500000, unroll_factor=1, vector_factor=1, total_iterations=1800000, cgra_rows=12, cgra_columns=12),
            NeuraDemo.Kernel(kernel_name="gemm.c", kernel_id=1, arrive_period=12582912, unroll_factor=1, vector_factor=1, total_iterations=2097152, cgra_rows=12, cgra_columns=12),
            #NeuraDemo.Kernel(kernel_name="spmv+conv.c", kernel_id=7, arrive_period=3840000, unroll_factor=1, vector_factor=8, total_iterations=480000, cgra_rows=4, cgra_columns=4)
        ]
    ]

    NeuraDemo.run_multiple_simulations_and_save_to_csv(baselineCase1, "Baseline", priority_bosting = False, num_cgras=1)  # one cgra is 12x12
    # NeuraDemo.run_multiple_simulations_and_save_to_csv(taskCase1, "NoBosting", priority_bosting = False, num_cgras=9) # one cgra is 4x4
    # NeuraDemo.run_multiple_simulations_and_save_to_csv(taskCase1, "Bosting", priority_bosting = True, num_cgras=9)    # one cgra is 4x4
