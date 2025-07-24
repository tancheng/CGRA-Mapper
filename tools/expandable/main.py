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
    # 静态内核数据 (名称: (排序ID, 总迭代次数, 静态执行时间))
    KERNEL_DATA = {
        "gemm.c": (0, 2097152, 4194304),          # 最大执行时间，排序ID=0
        "conv.c": (1, 262144, 524288),            # 次之，排序ID=1
        "spmv.c": (2, 65536, 131072),             # 排序ID=2
        "dtw.cpp": (3, 16384, 49152),             # 排序ID=3
        "mvt.c": (4, 16384, 49152),               # 与dtw执行时间相同，按名称排序，ID=4
        "fft.c": (5, 11264, 45056),               # 排序ID=5
        #"relu.c": (6, 4096, 8192),                # 排序ID=6
        #"histogram.cpp": (7, 4096, 8192),         # 与relu执行时间相同，按名称排序，ID=7
        "relu+histogram.c": (8, 4096, 8192),      # 与relu/histogram执行时间相同，ID=8
        "fir.cpp": (9, 2048, 4096),               # 排序ID=9
        "latnrm.c": (10, 128, 256)                # 最小执行时间，排序ID=10
    }
    # 静态内核数据 (名称: (排序ID, 总迭代次数, 静态执行时间))
    KERNEL_DATA = {
        "fir.cpp": (7, 2048, 4096),                # 静态执行时间4096，排序ID=6
        "latnrm.c": (8, 128, 256),                 # 静态执行时间256，排序ID=7（最小）
        "fft.c": (5, 11264, 45056),                # 静态执行时间45056，排序ID=4
        "dtw.cpp": (3, 16384, 49152),              # 静态执行时间49152，排序ID=1（字母序优先）
        "spmv.c": (2, 65536, 131072),              # 静态执行时间131072，排序ID=3
        "conv.c": (1, 262144, 524288),             # 静态执行时间524288，排序ID=2
        #"relu.c": (, 4096, 8192),                 # 排除排序
        #"histogram.cpp": (, 4096, 8192),          # 排除排序
        "mvt.c": (4, 16384, 49152),                # 静态执行时间49152，排序ID=5（字母序靠后）
        "gemm.c": (0, 2097152, 4194304),           # 静态执行时间4194304，排序ID=0（最大）
        "relu+histogram.c": (6, 4096, 8192)        # 静态执行时间8192，排序ID=6
    }

    CGRA_SIZES = [12, 4]  # 按照需求，先生成12的配置，再生成4的配置
    A_P = [3]*9 # 到达周期乘数列表
    #UNROLL_FACTORS = [4, 4, 2, 1, 4, 2, 4, 4, 4]  # unroll_factor列表
    UNROLL_FACTORS = [1] * 9  # unroll_factor列表
    VECTOR_FACTORS = [16, 1, 16, 16, 16, 16, 16, 16, 16]  # vector_factor列表

    # 确保所有列表长度一致
    lists = [KERNEL_DATA, A_P, UNROLL_FACTORS, VECTOR_FACTORS]
    if len(set(len(lst) for lst in lists)) != 1:
        raise ValueError(f"参数长度不一致: {[len(lst) for lst in lists]}")

    # 生成baselineCase1 (CGRA_SIZES=12)
    print("baselineCase6=[")
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
    print("\ntaskCase6=[")
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



if args.old_new == -1:
    # 调用函数生成输出
    generate_and_print_kernel_configs()
elif args.old_new == 0:
    # NeuraDemoArchive
    # baselineCase1=[
    #     [
    #         NeuraDemoArchive.Kernel(kernel_name="fir.cpp", kernel_id=8, arrive_period=600000, unroll_factor=1, vector_factor=8, total_iterations=300000, cgra_rows=4, cgra_columns=4),
    #         NeuraDemoArchive.Kernel(kernel_name="latnrm.c", kernel_id=3, arrive_period=3600000, unroll_factor=1, vector_factor=8, total_iterations=1200000, cgra_rows=4, cgra_columns=4),
    #         NeuraDemoArchive.Kernel(kernel_name="fft.c", kernel_id=4, arrive_period=3840000, unroll_factor=1, vector_factor=8, total_iterations=480000, cgra_rows=4, cgra_columns=4),
    #         NeuraDemoArchive.Kernel(kernel_name="dtw.cpp", kernel_id=5, arrive_period=3932160, unroll_factor=1, vector_factor=8, total_iterations=524288, cgra_rows=4, cgra_columns=4),
    #         NeuraDemoArchive.Kernel(kernel_name="spmv.c", kernel_id=6, arrive_period=4571136, unroll_factor=1, vector_factor=8, total_iterations=507904, cgra_rows=4, cgra_columns=4),
    #         NeuraDemoArchive.Kernel(kernel_name="conv.c", kernel_id=7, arrive_period=1200000, unroll_factor=1, vector_factor=8, total_iterations=400000, cgra_rows=4, cgra_columns=4),
    #         NeuraDemoArchive.Kernel(kernel_name="relu.c", kernel_id=2, arrive_period=4500000, unroll_factor=1, vector_factor=8, total_iterations=1000000, cgra_rows=4, cgra_columns=4),
    #         NeuraDemoArchive.Kernel(kernel_name="histogram.cpp", kernel_id=9, arrive_period=1048576, unroll_factor=1, vector_factor=8, total_iterations=262144, cgra_rows=4, cgra_columns=4),
    #         NeuraDemoArchive.Kernel(kernel_name="mvt.c", kernel_id=0, arrive_period=13500000, unroll_factor=1, vector_factor=8, total_iterations=1800000, cgra_rows=4, cgra_columns=4),
    #         NeuraDemoArchive.Kernel(kernel_name="gemm.c", kernel_id=1, arrive_period=12582912, unroll_factor=1, vector_factor=8, total_iterations=2097152, cgra_rows=4, cgra_columns=4),
    #         #NeuraDemoArchive.Kernel(kernel_name="relu+histogram.c", kernel_id=7, arrive_period=3840000, unroll_factor=1, vector_factor=8, total_iterations=480000, cgra_rows=4, cgra_columns=4)
    #     ]
    # ]
    pass
    # NeuraDemoArchive.run_multiple_simulations_and_save_to_csv(baselineCase1, "Baseline", priority_boosting = False, num_cgras=1)  # one cgra is 12x12
    # run_multiple_simulations_and_save_to_csv(taskCase1, "NoBosting", priority_boosting = False, num_cgras=9) # one cgra is 4x4
    # run_multiple_simulations_and_save_to_csv(taskCase1, "Bosting", priority_boosting = True, num_cgras=3)    # one cgra is 4x4
elif args.old_new == 1:
    # NeuraDemo
    # baselineCase1=[
    #     [
    #         NeuraDemo.Kernel(kernel_name="fir.cpp", kernel_id=8, arrive_period=600000, unroll_factor=1, vector_factor=1, total_iterations=300000, cgra_rows=12, cgra_columns=12),
    #         NeuraDemo.Kernel(kernel_name="latnrm.c", kernel_id=3, arrive_period=3600000, unroll_factor=1, vector_factor=1, total_iterations=1200000, cgra_rows=12, cgra_columns=12),
    #         NeuraDemo.Kernel(kernel_name="fft.c", kernel_id=4, arrive_period=3840000, unroll_factor=1, vector_factor=1, total_iterations=480000, cgra_rows=12, cgra_columns=12),
    #         NeuraDemo.Kernel(kernel_name="dtw.cpp", kernel_id=5, arrive_period=3932160, unroll_factor=1, vector_factor=1, total_iterations=524288, cgra_rows=12, cgra_columns=12),
    #         NeuraDemo.Kernel(kernel_name="spmv.c", kernel_id=6, arrive_period=4571136, unroll_factor=1, vector_factor=1, total_iterations=507904, cgra_rows=12, cgra_columns=12),
    #         NeuraDemo.Kernel(kernel_name="conv.c", kernel_id=7, arrive_period=1200000, unroll_factor=1, vector_factor=1, total_iterations=400000, cgra_rows=12, cgra_columns=12),
    #         NeuraDemo.Kernel(kernel_name="relu.c", kernel_id=2, arrive_period=4500000, unroll_factor=1, vector_factor=1, total_iterations=1000000, cgra_rows=12, cgra_columns=12),
    #         NeuraDemo.Kernel(kernel_name="histogram.cpp", kernel_id=9, arrive_period=1048576, unroll_factor=1, vector_factor=1, total_iterations=262144, cgra_rows=12, cgra_columns=12),
    #         NeuraDemo.Kernel(kernel_name="mvt.c", kernel_id=0, arrive_period=13500000, unroll_factor=1, vector_factor=1, total_iterations=1800000, cgra_rows=12, cgra_columns=12),
    #         NeuraDemo.Kernel(kernel_name="gemm.c", kernel_id=1, arrive_period=12582912, unroll_factor=1, vector_factor=1, total_iterations=2097152, cgra_rows=12, cgra_columns=12),
    #         #NeuraDemo.Kernel(kernel_name="spmv+conv.c", kernel_id=7, arrive_period=3840000, unroll_factor=1, vector_factor=8, total_iterations=480000, cgra_rows=4, cgra_columns=4)
    #     ]
    # ]

    # taskCase1=[
    #     [
    #         NeuraDemo.Kernel(kernel_name="fir.cpp", kernel_id=8, arrive_period=600000, unroll_factor=1, vector_factor=1, total_iterations=300000, cgra_rows=12, cgra_columns=12),
    #         NeuraDemo.Kernel(kernel_name="latnrm.c", kernel_id=3, arrive_period=3600000, unroll_factor=1, vector_factor=1, total_iterations=1200000, cgra_rows=12, cgra_columns=12),
    #         NeuraDemo.Kernel(kernel_name="fft.c", kernel_id=4, arrive_period=3840000, unroll_factor=1, vector_factor=1, total_iterations=480000, cgra_rows=12, cgra_columns=12),
    #         NeuraDemo.Kernel(kernel_name="dtw.cpp", kernel_id=5, arrive_period=3932160, unroll_factor=1, vector_factor=1, total_iterations=524288, cgra_rows=12, cgra_columns=12),
    #         NeuraDemo.Kernel(kernel_name="spmv.c", kernel_id=6, arrive_period=4571136, unroll_factor=1, vector_factor=1, total_iterations=507904, cgra_rows=12, cgra_columns=12),
    #         NeuraDemo.Kernel(kernel_name="conv.c", kernel_id=7, arrive_period=1200000, unroll_factor=1, vector_factor=1, total_iterations=400000, cgra_rows=12, cgra_columns=12),
    #         NeuraDemo.Kernel(kernel_name="relu.c", kernel_id=2, arrive_period=4500000, unroll_factor=1, vector_factor=1, total_iterations=1000000, cgra_rows=12, cgra_columns=12),
    #         NeuraDemo.Kernel(kernel_name="histogram.cpp", kernel_id=9, arrive_period=1048576, unroll_factor=1, vector_factor=1, total_iterations=262144, cgra_rows=12, cgra_columns=12),
    #         NeuraDemo.Kernel(kernel_name="mvt.c", kernel_id=0, arrive_period=13500000, unroll_factor=1, vector_factor=1, total_iterations=1800000, cgra_rows=12, cgra_columns=12),
    #         NeuraDemo.Kernel(kernel_name="gemm.c", kernel_id=1, arrive_period=12582912, unroll_factor=1, vector_factor=1, total_iterations=2097152, cgra_rows=12, cgra_columns=12),
    #         #NeuraDemo.Kernel(kernel_name="spmv+conv.c", kernel_id=7, arrive_period=3840000, unroll_factor=1, vector_factor=8, total_iterations=480000, cgra_rows=4, cgra_columns=4)
    #     ]
    # ]

    # NeuraDemo.run_multiple_simulations_and_save_to_csv(baselineCase1, "Baseline", priority_boosting = 0, num_cgras=1)  # one cgra is 12x12
    # NeuraDemo.run_multiple_simulations_and_save_to_csv(taskCase1, "BostingScalar", priority_boosting = 1, num_cgras=9) # one cgra is 4x4
    # NeuraDemo.run_multiple_simulations_and_save_to_csv(taskCase1, "BostingScalarFuse", priority_boosting = 2, num_cgras=9)    # one cgra is 4x4
    # NeuraDemo.run_multiple_simulations_and_save_to_csv(taskCase1, "BostingScalarFuseVector", priority_boosting = 3, num_cgras=9)    # one cgra is 4x4

    # NeuraDemo
    # baselineCase1=[
    #     [
    #         NeuraDemo.Kernel(kernel_name="fir.cpp", kernel_id=8, arrive_period=600000, unroll_factor=1, vector_factor=1, total_iterations=300000, cgra_rows=12, cgra_columns=12),
    #         NeuraDemo.Kernel(kernel_name="latnrm.c", kernel_id=3, arrive_period=3600000, unroll_factor=1, vector_factor=1, total_iterations=1200000, cgra_rows=12, cgra_columns=12),
    #         NeuraDemo.Kernel(kernel_name="fft.c", kernel_id=4, arrive_period=3840000, unroll_factor=1, vector_factor=1, total_iterations=480000, cgra_rows=12, cgra_columns=12),
    #         NeuraDemo.Kernel(kernel_name="dtw.cpp", kernel_id=5, arrive_period=3932160, unroll_factor=1, vector_factor=1, total_iterations=524288, cgra_rows=12, cgra_columns=12),
    #         NeuraDemo.Kernel(kernel_name="spmv.c", kernel_id=6, arrive_period=4571136, unroll_factor=1, vector_factor=1, total_iterations=507904, cgra_rows=12, cgra_columns=12),
    #         NeuraDemo.Kernel(kernel_name="conv.c", kernel_id=7, arrive_period=1200000, unroll_factor=1, vector_factor=1, total_iterations=400000, cgra_rows=12, cgra_columns=12),
    #         NeuraDemo.Kernel(kernel_name="relu.c", kernel_id=2, arrive_period=4500000, unroll_factor=1, vector_factor=1, total_iterations=1000000, cgra_rows=12, cgra_columns=12),
    #         NeuraDemo.Kernel(kernel_name="histogram.cpp", kernel_id=9, arrive_period=1048576, unroll_factor=1, vector_factor=1, total_iterations=262144, cgra_rows=12, cgra_columns=12),
    #         NeuraDemo.Kernel(kernel_name="mvt.c", kernel_id=0, arrive_period=13500000, unroll_factor=1, vector_factor=1, total_iterations=1800000, cgra_rows=12, cgra_columns=12),
    #         NeuraDemo.Kernel(kernel_name="gemm.c", kernel_id=1, arrive_period=12582912, unroll_factor=1, vector_factor=1, total_iterations=2097152, cgra_rows=12, cgra_columns=12),
    #         #NeuraDemo.Kernel(kernel_name="spmv+conv.c", kernel_id=7, arrive_period=3840000, unroll_factor=1, vector_factor=8, total_iterations=480000, cgra_rows=4, cgra_columns=4)
    #     ]
    # ]

    # taskCase1=[
    #     [
    #         NeuraDemo.Kernel(kernel_name="fir.cpp", kernel_id=8, arrive_period=600000, unroll_factor=1, vector_factor=1, total_iterations=300000, cgra_rows=12, cgra_columns=12),
    #         NeuraDemo.Kernel(kernel_name="latnrm.c", kernel_id=3, arrive_period=3600000, unroll_factor=1, vector_factor=1, total_iterations=1200000, cgra_rows=12, cgra_columns=12),
    #         NeuraDemo.Kernel(kernel_name="fft.c", kernel_id=4, arrive_period=3840000, unroll_factor=1, vector_factor=1, total_iterations=480000, cgra_rows=12, cgra_columns=12),
    #         NeuraDemo.Kernel(kernel_name="dtw.cpp", kernel_id=5, arrive_period=3932160, unroll_factor=1, vector_factor=1, total_iterations=524288, cgra_rows=12, cgra_columns=12),
    #         NeuraDemo.Kernel(kernel_name="spmv.c", kernel_id=6, arrive_period=4571136, unroll_factor=1, vector_factor=1, total_iterations=507904, cgra_rows=12, cgra_columns=12),
    #         NeuraDemo.Kernel(kernel_name="conv.c", kernel_id=7, arrive_period=1200000, unroll_factor=1, vector_factor=1, total_iterations=400000, cgra_rows=12, cgra_columns=12),
    #         NeuraDemo.Kernel(kernel_name="relu.c", kernel_id=2, arrive_period=4500000, unroll_factor=1, vector_factor=1, total_iterations=1000000, cgra_rows=12, cgra_columns=12),
    #         NeuraDemo.Kernel(kernel_name="histogram.cpp", kernel_id=9, arrive_period=1048576, unroll_factor=1, vector_factor=1, total_iterations=262144, cgra_rows=12, cgra_columns=12),
    #         NeuraDemo.Kernel(kernel_name="mvt.c", kernel_id=0, arrive_period=13500000, unroll_factor=1, vector_factor=1, total_iterations=1800000, cgra_rows=12, cgra_columns=12),
    #         NeuraDemo.Kernel(kernel_name="gemm.c", kernel_id=1, arrive_period=12582912, unroll_factor=1, vector_factor=1, total_iterations=2097152, cgra_rows=12, cgra_columns=12),
    #         #NeuraDemo.Kernel(kernel_name="spmv+conv.c", kernel_id=7, arrive_period=3840000, unroll_factor=1, vector_factor=8, total_iterations=480000, cgra_rows=4, cgra_columns=4)
    #     ]
    # ]

    # NeuraDemo.run_multiple_simulations_and_save_to_csv(baselineCase1, "Baseline", priority_boosting = 0, num_cgras=1)  # one cgra is 12x12
    # NeuraDemo.run_multiple_simulations_and_save_to_csv(taskCase1, "BostingScalar", priority_boosting = 1, num_cgras=9) # one cgra is 4x4
    # NeuraDemo.run_multiple_simulations_and_save_to_csv(taskCase1, "BostingScalarFuse", priority_boosting = 2, num_cgras=9)    # one cgra is 4x4
    # NeuraDemo.run_multiple_simulations_and_save_to_csv(taskCase1, "BostingScalarFuseVector", priority_boosting = 3, num_cgras=9)    # one cgra is 4x4

    baselineCase6=[
        [
            NeuraDemo.Kernel(kernel_name="fir.cpp", kernel_id=7, arrive_period=12288, unroll_factor=1, vector_factor=16, total_iterations=2048, cgra_rows=12, cgra_columns=12),
            NeuraDemo.Kernel(kernel_name="latnrm.c", kernel_id=8, arrive_period=768, unroll_factor=1, vector_factor=1, total_iterations=128, cgra_rows=12, cgra_columns=12),
            NeuraDemo.Kernel(kernel_name="fft.c", kernel_id=5, arrive_period=135168, unroll_factor=1, vector_factor=16, total_iterations=11264, cgra_rows=12, cgra_columns=12),
            NeuraDemo.Kernel(kernel_name="dtw.cpp", kernel_id=3, arrive_period=147456, unroll_factor=1, vector_factor=16, total_iterations=16384, cgra_rows=12, cgra_columns=12),
            NeuraDemo.Kernel(kernel_name="spmv.c", kernel_id=2, arrive_period=393216, unroll_factor=1, vector_factor=16, total_iterations=65536, cgra_rows=12, cgra_columns=12),
            NeuraDemo.Kernel(kernel_name="conv.c", kernel_id=1, arrive_period=1572864, unroll_factor=1, vector_factor=16, total_iterations=262144, cgra_rows=12, cgra_columns=12),
            NeuraDemo.Kernel(kernel_name="mvt.c", kernel_id=4, arrive_period=147456, unroll_factor=1, vector_factor=16, total_iterations=16384, cgra_rows=12, cgra_columns=12),
            NeuraDemo.Kernel(kernel_name="gemm.c", kernel_id=0, arrive_period=12582912, unroll_factor=1, vector_factor=16, total_iterations=2097152, cgra_rows=12, cgra_columns=12),
            NeuraDemo.Kernel(kernel_name="relu+histogram.c", kernel_id=6, arrive_period=24576, unroll_factor=1, vector_factor=16, total_iterations=4096, cgra_rows=12, cgra_columns=12),
        ]
    ]

    # taskCase6=[
    #     [
    #         NeuraDemo.Kernel(kernel_name="fir.cpp", kernel_id=7, arrive_period=12288, unroll_factor=1, vector_factor=16, total_iterations=2048, cgra_rows=4, cgra_columns=4),
    #         NeuraDemo.Kernel(kernel_name="latnrm.c", kernel_id=8, arrive_period=768, unroll_factor=1, vector_factor=1, total_iterations=128, cgra_rows=4, cgra_columns=4),
    #         NeuraDemo.Kernel(kernel_name="fft.c", kernel_id=5, arrive_period=135168, unroll_factor=1, vector_factor=16, total_iterations=11264, cgra_rows=4, cgra_columns=4),
    #         NeuraDemo.Kernel(kernel_name="dtw.cpp", kernel_id=3, arrive_period=147456, unroll_factor=1, vector_factor=16, total_iterations=16384, cgra_rows=4, cgra_columns=4),
    #         NeuraDemo.Kernel(kernel_name="spmv.c", kernel_id=2, arrive_period=393216, unroll_factor=1, vector_factor=16, total_iterations=65536, cgra_rows=4, cgra_columns=4),
    #         NeuraDemo.Kernel(kernel_name="conv.c", kernel_id=1, arrive_period=1572864, unroll_factor=1, vector_factor=16, total_iterations=262144, cgra_rows=4, cgra_columns=4),
    #         NeuraDemo.Kernel(kernel_name="mvt.c", kernel_id=4, arrive_period=147456, unroll_factor=1, vector_factor=16, total_iterations=16384, cgra_rows=4, cgra_columns=4),
    #         NeuraDemo.Kernel(kernel_name="gemm.c", kernel_id=0, arrive_period=12582912, unroll_factor=1, vector_factor=16, total_iterations=2097152, cgra_rows=4, cgra_columns=4),
    #         NeuraDemo.Kernel(kernel_name="relu+histogram.c", kernel_id=6, arrive_period=24576, unroll_factor=1, vector_factor=16, total_iterations=4096, cgra_rows=4, cgra_columns=4),
    #     ]
    # ]
    NeuraDemo.run_multiple_simulations_and_save_to_csv(baselineCase6, "Baseline", priority_boosting = 0, num_cgras=1)  # one cgra is 12x12
    NeuraDemo.run_multiple_simulations_and_save_to_csv(taskCase6, "NoBosting", priority_boosting = 0, num_cgras=9)  # one cgra is 4x4
    # NeuraDemo.run_multiple_simulations_and_save_to_csv(taskCase6, "BostingScalar", priority_boosting = 1, num_cgras=9) # one cgra is 4x4
    # NeuraDemo.run_multiple_simulations_and_save_to_csv(taskCase6, "BostingScalarFuse", priority_boosting = 2, num_cgras=9)    # one cgra is 4x4
    # NeuraDemo.run_multiple_simulations_and_save_to_csv(taskCase6, "BostingScalarFuseVector", priority_boosting = 3, num_cgras=9)    # one cgra is 4x4
