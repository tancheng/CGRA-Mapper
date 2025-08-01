import argparse
import NeuraDemo
import NeuraDemoArchive

parser = argparse.ArgumentParser()
parser.add_argument('--old-new',
                    type=int,
                    default=0)
args, _ = parser.parse_known_args()



# ========== 配置区域 ==========
# 静态内核数据 (名称: (排序ID, 总迭代次数, 静态执行时间))
KERNEL_DATA = {
    "fir.cpp": (7, 2048, 4096),                  # 静态执行时间4096，排序ID=6 (original iteration count)
    "latnrm.c": (8, 1280, 2560),
    "fft.c": (2, 112640, 450560),                 # 静态执行时间450560，排序ID=4 (updated iteration count, original execution time)
    "dtw.cpp": (4, 16384, 49152),                # 静态执行时间49152，排序ID=1 (original data)
    "spmv.c": (3, 65536, 262144),                # 静态执行时间131072，排序ID=3 (original data)
    "conv.c": (1, 655360, 1310720),              # 静态执行时间1310720，排序ID=2 (updated iteration count, original execution time)
    #"relu.c": (, 4096, 8192),                   # 排除排序
    #"histogram.cpp": (, 4096, 8192),            # 排除排序
    "mvt.c": (5, 16384, 49152),                  # 静态执行时间49152，排序ID=5 (original data)
    "gemm.c": (0, 2097152, 8388608),             # 静态执行时间4194304，排序ID=0 (original data)
    "relu+histogram.c": (6, 262144, 2097152)          # 静态执行时间8192，排序ID=6 (original data)
}

# 每个case的配置字典 (case_id: [A_P, UNROLL_FACTORS, VECTOR_FACTORS])
CASE_CONFIGS = {
    # 1: {
    #     'A_P': [163840, 163840, 163840, 655360, 655360, 2621440, 163840, 2621440, 81920],
    #     'UNROLL_FACTORS': [1]*9,
    #     'VECTOR_FACTORS': [1]*9
    # },
    # 2: {
    #     'A_P': [163840, 163840, 163840, 409600, 409600, 2621440, 163840, 2621440, 163840],
    #     'UNROLL_FACTORS': [1,2,2,1,2,2,2,1,2],
    #     'VECTOR_FACTORS': [4, 1, 1, 4, 1, 1, 1, 4, 1]
    # },
    # 3: {
    #     'A_P': [163840, 163840, 163840, 409600, 409600, 2621440, 163840, 2621440, 163840],
    #     'UNROLL_FACTORS': [1,4,2,1,4,4,4,1,4],
    #     'VECTOR_FACTORS': [8, 1, 1, 8, 1, 1, 1, 8, 1]
    # },
    # 4: {
    #     'A_P': [163840, 163840, 163840, 655360, 655360, 3276800, 102400, 3276800, 102400],
    #     'UNROLL_FACTORS': [1,4,1,1,4,4,4,1,4],
    #     'VECTOR_FACTORS': [16, 1, 16, 16, 1, 1, 1, 16, 1]
    # },
    # 5: {
    #     'A_P': [163840, 163840, 163840, 655360, 655360, 3276800, 163840, 3276800, 163840],
    #     'UNROLL_FACTORS': [1,4,1,2,4,4,4,1,4],
    #     'VECTOR_FACTORS': [16, 1, 1, 16, 1, 1, 1, 16, 1]
    # },
    # 6: {
    #     'A_P': [204800, 204800, 204800, 819200, 819200, 5242880, 204800, 5242880, 204800],
    #     'UNROLL_FACTORS': [1,4,1,1,4,4,4,1,4],
    #     'VECTOR_FACTORS': [16, 1, 16, 16, 1, 1, 1, 16, 1]
    # },
    72: {
        'A_P': [204800, 204800, 5242880, 665360, 665360, 5242880, 204800, 5242880, 204800],
        'UNROLL_FACTORS': [1,4,1,1,4,4,4,1,4],
        'VECTOR_FACTORS': [16, 1, 16, 16, 1, 1, 1, 16, 1]
    },
    74: {
        'A_P': [204800, 204800, 5242880, 665360, 665360, 5242880, 204800, 5242880, 204800],
        'UNROLL_FACTORS': [1,4,1,1,4,4,4,1,4],
        'VECTOR_FACTORS': [16, 1, 16, 16, 1, 1, 1, 16, 1]
    },
    75: {
        'A_P': [204800, 204800, 5242880, 665360, 665360, 5242880, 204800, 5242880, 204800],
        'UNROLL_FACTORS': [1,4,1,1,4,4,4,1,4],
        'VECTOR_FACTORS': [16, 1, 16, 16, 1, 1, 1, 16, 1]
    }
}
# TODO：要不要所有 arrive_times 都加1
# TODO: 把 scalar 运行时间或者到达次数加大
# ========== 生成代码 ==========
def generate_cases():
    for case_id, config in CASE_CONFIGS.items():
        A_P = config['A_P']
        UNROLL_FACTORS = config['UNROLL_FACTORS']
        VECTOR_FACTORS = config['VECTOR_FACTORS']

        # 验证参数长度
        lists = [KERNEL_DATA, A_P, UNROLL_FACTORS, VECTOR_FACTORS]
        if len(set(len(lst) for lst in lists if lst)) > 1:  # 允许空列表
            raise ValueError(f"Case{case_id}参数长度不一致: {[len(lst) for lst in lists]}")

        # TODO: baseline 的 spmv unroll 为2, relu+histogram unroll 为1
        # 生成baseCase (CGRA=12)
        print(f"\n  baselineCase{case_id}=[")
        print("         [")
        for i, (kernel_name, (kernel_id, total_iters, _)) in enumerate(KERNEL_DATA.items()):
            print(f'            NeuraDemo.Kernel('
                  f'kernel_name="{kernel_name}", kernel_id={kernel_id}, '
                  f'arrive_period={A_P[i] if A_P else 0}, '
                  f'unroll_factor={UNROLL_FACTORS[i]}, '
                  f'vector_factor={VECTOR_FACTORS[i]}, '
                  f'total_iterations={total_iters}, '
                  f'cgra_rows=20, cgra_columns=20),')   # f'cgra_rows=16, cgra_columns=16),'
        print("         ]\n]")

        # 生成taskCase (CGRA=4)
        print(f"\n  taskCase{case_id}=[")
        print("         [")
        for i, (kernel_name, (kernel_id, total_iters, _)) in enumerate(KERNEL_DATA.items()):
            print(f'            NeuraDemo.Kernel('
                  f'kernel_name="{kernel_name}", kernel_id={kernel_id}, '
                  f'arrive_period={A_P[i] if A_P else 0}, '
                  f'unroll_factor={UNROLL_FACTORS[i]}, '
                  f'vector_factor={VECTOR_FACTORS[i]}, '
                  f'total_iterations={total_iters}, '
                  f'cgra_rows=4, cgra_columns=4),')
        print("         ]\n]")


if args.old_new == -1:
    # 调用函数生成输出
    generate_cases()
elif args.old_new == 0:
    # NeuraDemoArchiveArchive
    taskCase7=[
        [
            NeuraDemoArchive.Kernel(kernel_name="fir.cpp", kernel_id=7, arrive_period=173840, unroll_factor=1, vector_factor=16, total_iterations=2048, cgra_rows=4, cgra_columns=4),
            NeuraDemoArchive.Kernel(kernel_name="latnrm.c", kernel_id=8, arrive_period=173840, unroll_factor=4, vector_factor=1, total_iterations=1280, cgra_rows=4, cgra_columns=4),
            NeuraDemoArchive.Kernel(kernel_name="fft.c", kernel_id=2, arrive_period=173840, unroll_factor=1, vector_factor=16, total_iterations=112640, cgra_rows=4, cgra_columns=4),
            NeuraDemoArchive.Kernel(kernel_name="dtw.cpp", kernel_id=4, arrive_period=665360, unroll_factor=1, vector_factor=16, total_iterations=16384, cgra_rows=4, cgra_columns=4),
            NeuraDemoArchive.Kernel(kernel_name="spmv.c", kernel_id=3, arrive_period=665360, unroll_factor=4, vector_factor=1, total_iterations=65536, cgra_rows=4, cgra_columns=4),
            NeuraDemoArchive.Kernel(kernel_name="conv.c", kernel_id=1, arrive_period=3286800, unroll_factor=4, vector_factor=1, total_iterations=655360, cgra_rows=4, cgra_columns=4),
            NeuraDemoArchive.Kernel(kernel_name="mvt.c", kernel_id=5, arrive_period=173840, unroll_factor=4, vector_factor=1, total_iterations=16384, cgra_rows=4, cgra_columns=4),
            NeuraDemoArchive.Kernel(kernel_name="gemm.c", kernel_id=0, arrive_period=3286800, unroll_factor=1, vector_factor=16, total_iterations=2097152, cgra_rows=4, cgra_columns=4),
            NeuraDemoArchive.Kernel(kernel_name="relu+histogram.c", kernel_id=6, arrive_period=173840, unroll_factor=4, vector_factor=1, total_iterations=360000, cgra_rows=4, cgra_columns=4),
            #NeuraDemoArchive.Kernel(kernel_name="relu+histogram.c", kernel_id=6, arrive_period=10960000, unroll_factor=4, vector_factor=1, total_iterations=4096, cgra_rows=4, cgra_columns=4)
        ]
    ]
    # TODO： arrive_period decouple with execution time
    # TODO: case 1-6 + N
    #NeuraDemoArchive.run_multiple_simulations_and_save_to_csv(baselineCase7, "Baseline", priority_boosting = 0, kernel_case=8, num_cgras=1)  # one cgra is 12x12
    NeuraDemoArchive.run_multiple_simulations_and_save_to_csv(taskCase7, "NoBosting", priority_boosting = 0, kernel_case=8, num_cgras=9)  # one cgra is 4x4
    NeuraDemoArchive.run_multiple_simulations_and_save_to_csv(taskCase7, "BostingScalar", priority_boosting = 1, kernel_case=8, num_cgras=9) # one cgra is 4x4
    #NeuraDemoArchive.run_multiple_simulations_and_save_to_csv(taskCase7, "BostingScalarFuse", priority_boosting = 2, kernel_case=8, num_cgras=9)    # one cgra is 4x4
    #NeuraDemo.run_multiple_simulations_and_save_to_csv(taskCase7, "BostingScalarFuseVector", priority_boosting = 3, kernel_case=8, num_cgras=9)    # one cgra is 4x4
elif args.old_new == 1:
    baselineCase1=[
            [
                NeuraDemo.Kernel(kernel_name="fir.cpp", kernel_id=7, arrive_period=163840, unroll_factor=1, vector_factor=1, total_iterations=2048, cgra_rows=12, cgra_columns=12),
                NeuraDemo.Kernel(kernel_name="latnrm.c", kernel_id=8, arrive_period=163840, unroll_factor=1, vector_factor=1, total_iterations=1280, cgra_rows=12, cgra_columns=12),
                NeuraDemo.Kernel(kernel_name="fft.c", kernel_id=2, arrive_period=163840, unroll_factor=1, vector_factor=1, total_iterations=112640, cgra_rows=12, cgra_columns=12),
                NeuraDemo.Kernel(kernel_name="dtw.cpp", kernel_id=4, arrive_period=655360, unroll_factor=1, vector_factor=1, total_iterations=16384, cgra_rows=12, cgra_columns=12),
                NeuraDemo.Kernel(kernel_name="spmv.c", kernel_id=3, arrive_period=655360, unroll_factor=1, vector_factor=1, total_iterations=65536, cgra_rows=12, cgra_columns=12),
                NeuraDemo.Kernel(kernel_name="conv.c", kernel_id=1, arrive_period=2621440, unroll_factor=1, vector_factor=1, total_iterations=655360, cgra_rows=12, cgra_columns=12),
                NeuraDemo.Kernel(kernel_name="mvt.c", kernel_id=5, arrive_period=163840, unroll_factor=1, vector_factor=1, total_iterations=16384, cgra_rows=12, cgra_columns=12),
                NeuraDemo.Kernel(kernel_name="gemm.c", kernel_id=0, arrive_period=2621440, unroll_factor=1, vector_factor=1, total_iterations=2097152, cgra_rows=12, cgra_columns=12),
                NeuraDemo.Kernel(kernel_name="relu+histogram.c", kernel_id=6, arrive_period=81920, unroll_factor=1, vector_factor=1, total_iterations=262144, cgra_rows=12, cgra_columns=12),
            ]
    ]

    taskCase1=[
            [
                NeuraDemo.Kernel(kernel_name="fir.cpp", kernel_id=7, arrive_period=163840, unroll_factor=1, vector_factor=1, total_iterations=2048, cgra_rows=4, cgra_columns=4),
                NeuraDemo.Kernel(kernel_name="latnrm.c", kernel_id=8, arrive_period=163840, unroll_factor=1, vector_factor=1, total_iterations=1280, cgra_rows=4, cgra_columns=4),
                NeuraDemo.Kernel(kernel_name="fft.c", kernel_id=2, arrive_period=163840, unroll_factor=1, vector_factor=1, total_iterations=112640, cgra_rows=4, cgra_columns=4),
                NeuraDemo.Kernel(kernel_name="dtw.cpp", kernel_id=4, arrive_period=655360, unroll_factor=1, vector_factor=1, total_iterations=16384, cgra_rows=4, cgra_columns=4),
                NeuraDemo.Kernel(kernel_name="spmv.c", kernel_id=3, arrive_period=655360, unroll_factor=1, vector_factor=1, total_iterations=65536, cgra_rows=4, cgra_columns=4),
                NeuraDemo.Kernel(kernel_name="conv.c", kernel_id=1, arrive_period=2621440, unroll_factor=1, vector_factor=1, total_iterations=655360, cgra_rows=4, cgra_columns=4),
                NeuraDemo.Kernel(kernel_name="mvt.c", kernel_id=5, arrive_period=163840, unroll_factor=1, vector_factor=1, total_iterations=16384, cgra_rows=4, cgra_columns=4),
                NeuraDemo.Kernel(kernel_name="gemm.c", kernel_id=0, arrive_period=2621440, unroll_factor=1, vector_factor=1, total_iterations=2097152, cgra_rows=4, cgra_columns=4),
                NeuraDemo.Kernel(kernel_name="relu+histogram.c", kernel_id=6, arrive_period=81920, unroll_factor=1, vector_factor=1, total_iterations=262144, cgra_rows=4, cgra_columns=4),
            ]
    ]


    NeuraDemo.run_multiple_simulations_and_save_to_csv(baselineCase1, "Baseline", priority_boosting = 0, kernel_case=1, num_cgras=1)  # one cgra is 12x12
    NeuraDemo.run_multiple_simulations_and_save_to_csv(taskCase1, "NoBosting", priority_boosting = 0, kernel_case=1, num_cgras=9)  # one cgra is 4x4
    NeuraDemo.run_multiple_simulations_and_save_to_csv(taskCase1, "BostingScalar", priority_boosting = 1, kernel_case=1, num_cgras=9) # one cgra is 4x4
    NeuraDemo.run_multiple_simulations_and_save_to_csv(taskCase1, "BostingScalarFuse", priority_boosting = 2, kernel_case=1, num_cgras=9)    # one cgra is 4x4
    NeuraDemo.run_multiple_simulations_and_save_to_csv(taskCase1, "BostingScalarFuseVector", priority_boosting = 3, kernel_case=1, num_cgras=9)    # one cgra is 4x4



elif args.old_new == 2:
    baselineCase2=[
            [
                NeuraDemo.Kernel(kernel_name="fir.cpp", kernel_id=7, arrive_period=163840, unroll_factor=1, vector_factor=4, total_iterations=2048, cgra_rows=12, cgra_columns=12),
                NeuraDemo.Kernel(kernel_name="latnrm.c", kernel_id=8, arrive_period=163840, unroll_factor=2, vector_factor=1, total_iterations=1280, cgra_rows=12, cgra_columns=12),
                NeuraDemo.Kernel(kernel_name="fft.c", kernel_id=2, arrive_period=163840, unroll_factor=1, vector_factor=1, total_iterations=112640, cgra_rows=12, cgra_columns=12),
                NeuraDemo.Kernel(kernel_name="dtw.cpp", kernel_id=4, arrive_period=409600, unroll_factor=1, vector_factor=4, total_iterations=16384, cgra_rows=12, cgra_columns=12),
                NeuraDemo.Kernel(kernel_name="spmv.c", kernel_id=3, arrive_period=409600, unroll_factor=2, vector_factor=1, total_iterations=65536, cgra_rows=12, cgra_columns=12),
                NeuraDemo.Kernel(kernel_name="conv.c", kernel_id=1, arrive_period=2621440, unroll_factor=2, vector_factor=1, total_iterations=655360, cgra_rows=12, cgra_columns=12),
                NeuraDemo.Kernel(kernel_name="mvt.c", kernel_id=5, arrive_period=163840, unroll_factor=2, vector_factor=1, total_iterations=16384, cgra_rows=12, cgra_columns=12),
                NeuraDemo.Kernel(kernel_name="gemm.c", kernel_id=0, arrive_period=2621440, unroll_factor=1, vector_factor=4, total_iterations=2097152, cgra_rows=12, cgra_columns=12),
                NeuraDemo.Kernel(kernel_name="relu+histogram.c", kernel_id=6, arrive_period=163840, unroll_factor=1, vector_factor=1, total_iterations=262144, cgra_rows=12, cgra_columns=12),
            ]
    ]

    taskCase2=[
            [
                NeuraDemo.Kernel(kernel_name="fir.cpp", kernel_id=7, arrive_period=163840, unroll_factor=1, vector_factor=4, total_iterations=2048, cgra_rows=4, cgra_columns=4),
                NeuraDemo.Kernel(kernel_name="latnrm.c", kernel_id=8, arrive_period=163840, unroll_factor=2, vector_factor=1, total_iterations=1280, cgra_rows=4, cgra_columns=4),
                NeuraDemo.Kernel(kernel_name="fft.c", kernel_id=2, arrive_period=163840, unroll_factor=2, vector_factor=1, total_iterations=112640, cgra_rows=4, cgra_columns=4),
                NeuraDemo.Kernel(kernel_name="dtw.cpp", kernel_id=4, arrive_period=409600, unroll_factor=1, vector_factor=4, total_iterations=16384, cgra_rows=4, cgra_columns=4),
                NeuraDemo.Kernel(kernel_name="spmv.c", kernel_id=3, arrive_period=409600, unroll_factor=2, vector_factor=1, total_iterations=65536, cgra_rows=4, cgra_columns=4),
                NeuraDemo.Kernel(kernel_name="conv.c", kernel_id=1, arrive_period=2621440, unroll_factor=2, vector_factor=1, total_iterations=655360, cgra_rows=4, cgra_columns=4),
                NeuraDemo.Kernel(kernel_name="mvt.c", kernel_id=5, arrive_period=163840, unroll_factor=2, vector_factor=1, total_iterations=16384, cgra_rows=4, cgra_columns=4),
                NeuraDemo.Kernel(kernel_name="gemm.c", kernel_id=0, arrive_period=2621440, unroll_factor=1, vector_factor=4, total_iterations=2097152, cgra_rows=4, cgra_columns=4),
                NeuraDemo.Kernel(kernel_name="relu+histogram.c", kernel_id=6, arrive_period=163840, unroll_factor=2, vector_factor=1, total_iterations=262144, cgra_rows=4, cgra_columns=4),
            ]
    ]
    NeuraDemo.run_multiple_simulations_and_save_to_csv(baselineCase2, "Baseline", priority_boosting = 0, kernel_case=2, num_cgras=1)  # one cgra is 12x12
    NeuraDemo.run_multiple_simulations_and_save_to_csv(taskCase2, "NoBosting", priority_boosting = 0, kernel_case=2, num_cgras=9)  # one cgra is 4x4
    NeuraDemo.run_multiple_simulations_and_save_to_csv(taskCase2, "BostingScalar", priority_boosting = 1, kernel_case=2, num_cgras=9) # one cgra is 4x4
    NeuraDemo.run_multiple_simulations_and_save_to_csv(taskCase2, "BostingScalarFuse", priority_boosting = 2, kernel_case=2, num_cgras=9)    # one cgra is 4x4
    NeuraDemo.run_multiple_simulations_and_save_to_csv(taskCase2, "BostingScalarFuseVector", priority_boosting = 3, kernel_case=2, num_cgras=9)    # one cgra is 4x4


elif args.old_new == 3:
    baselineCase3=[
            [
                NeuraDemo.Kernel(kernel_name="fir.cpp", kernel_id=7, arrive_period=163840, unroll_factor=1, vector_factor=8, total_iterations=2048, cgra_rows=12, cgra_columns=12),
                NeuraDemo.Kernel(kernel_name="latnrm.c", kernel_id=8, arrive_period=163840, unroll_factor=4, vector_factor=1, total_iterations=1280, cgra_rows=12, cgra_columns=12),
                NeuraDemo.Kernel(kernel_name="fft.c", kernel_id=2, arrive_period=163840, unroll_factor=1, vector_factor=1, total_iterations=112640, cgra_rows=12, cgra_columns=12),
                NeuraDemo.Kernel(kernel_name="dtw.cpp", kernel_id=4, arrive_period=409600, unroll_factor=1, vector_factor=8, total_iterations=16384, cgra_rows=12, cgra_columns=12),
                NeuraDemo.Kernel(kernel_name="spmv.c", kernel_id=3, arrive_period=409600, unroll_factor=2, vector_factor=1, total_iterations=65536, cgra_rows=12, cgra_columns=12),
                NeuraDemo.Kernel(kernel_name="conv.c", kernel_id=1, arrive_period=2621440, unroll_factor=4, vector_factor=1, total_iterations=655360, cgra_rows=12, cgra_columns=12),
                NeuraDemo.Kernel(kernel_name="mvt.c", kernel_id=5, arrive_period=163840, unroll_factor=4, vector_factor=1, total_iterations=16384, cgra_rows=12, cgra_columns=12),
                NeuraDemo.Kernel(kernel_name="gemm.c", kernel_id=0, arrive_period=2621440, unroll_factor=1, vector_factor=8, total_iterations=2097152, cgra_rows=12, cgra_columns=12),
                NeuraDemo.Kernel(kernel_name="relu+histogram.c", kernel_id=6, arrive_period=163840, unroll_factor=1, vector_factor=1, total_iterations=262144, cgra_rows=12, cgra_columns=12),
            ]
    ]

    taskCase3=[
            [
                NeuraDemo.Kernel(kernel_name="fir.cpp", kernel_id=7, arrive_period=163840, unroll_factor=1, vector_factor=8, total_iterations=2048, cgra_rows=4, cgra_columns=4),
                NeuraDemo.Kernel(kernel_name="latnrm.c", kernel_id=8, arrive_period=163840, unroll_factor=4, vector_factor=1, total_iterations=1280, cgra_rows=4, cgra_columns=4),
                NeuraDemo.Kernel(kernel_name="fft.c", kernel_id=2, arrive_period=163840, unroll_factor=2, vector_factor=1, total_iterations=112640, cgra_rows=4, cgra_columns=4),
                NeuraDemo.Kernel(kernel_name="dtw.cpp", kernel_id=4, arrive_period=409600, unroll_factor=1, vector_factor=8, total_iterations=16384, cgra_rows=4, cgra_columns=4),
                NeuraDemo.Kernel(kernel_name="spmv.c", kernel_id=3, arrive_period=409600, unroll_factor=4, vector_factor=1, total_iterations=65536, cgra_rows=4, cgra_columns=4),
                NeuraDemo.Kernel(kernel_name="conv.c", kernel_id=1, arrive_period=2621440, unroll_factor=4, vector_factor=1, total_iterations=655360, cgra_rows=4, cgra_columns=4),
                NeuraDemo.Kernel(kernel_name="mvt.c", kernel_id=5, arrive_period=163840, unroll_factor=4, vector_factor=1, total_iterations=16384, cgra_rows=4, cgra_columns=4),
                NeuraDemo.Kernel(kernel_name="gemm.c", kernel_id=0, arrive_period=2621440, unroll_factor=1, vector_factor=8, total_iterations=2097152, cgra_rows=4, cgra_columns=4),
                NeuraDemo.Kernel(kernel_name="relu+histogram.c", kernel_id=6, arrive_period=163840, unroll_factor=4, vector_factor=1, total_iterations=262144, cgra_rows=4, cgra_columns=4),
            ]
    ]
    NeuraDemo.run_multiple_simulations_and_save_to_csv(baselineCase3, "Baseline", priority_boosting = 0, kernel_case=3, num_cgras=1)  # one cgra is 12x12
    NeuraDemo.run_multiple_simulations_and_save_to_csv(taskCase3, "NoBosting", priority_boosting = 0, kernel_case=3, num_cgras=9)  # one cgra is 4x4
    NeuraDemo.run_multiple_simulations_and_save_to_csv(taskCase3, "BostingScalar", priority_boosting = 1, kernel_case=3, num_cgras=9) # one cgra is 4x4
    NeuraDemo.run_multiple_simulations_and_save_to_csv(taskCase3, "BostingScalarFuse", priority_boosting = 2, kernel_case=3, num_cgras=9)    # one cgra is 4x4
    NeuraDemo.run_multiple_simulations_and_save_to_csv(taskCase3, "BostingScalarFuseVector", priority_boosting = 3, kernel_case=3, num_cgras=9)    # one cgra is 4x4


elif args.old_new == 4:
    baselineCase5=[
        [
            NeuraDemo.Kernel(kernel_name="fir.cpp", kernel_id=7, arrive_period=163840, unroll_factor=1, vector_factor=16, total_iterations=2048, cgra_rows=12, cgra_columns=12),
            NeuraDemo.Kernel(kernel_name="latnrm.c", kernel_id=8, arrive_period=163840, unroll_factor=4, vector_factor=1, total_iterations=1280, cgra_rows=12, cgra_columns=12),
            NeuraDemo.Kernel(kernel_name="fft.c", kernel_id=2, arrive_period=163840, unroll_factor=1, vector_factor=1, total_iterations=112640, cgra_rows=12, cgra_columns=12),
            NeuraDemo.Kernel(kernel_name="dtw.cpp", kernel_id=4, arrive_period=665360, unroll_factor=1, vector_factor=16, total_iterations=16384, cgra_rows=12, cgra_columns=12),
            NeuraDemo.Kernel(kernel_name="spmv.c", kernel_id=3, arrive_period=665360, unroll_factor=2, vector_factor=1, total_iterations=65536, cgra_rows=12, cgra_columns=12),
            NeuraDemo.Kernel(kernel_name="conv.c", kernel_id=1, arrive_period=3276800, unroll_factor=4, vector_factor=1, total_iterations=655360, cgra_rows=12, cgra_columns=12),
            NeuraDemo.Kernel(kernel_name="mvt.c", kernel_id=5, arrive_period=102400, unroll_factor=4, vector_factor=1, total_iterations=16384, cgra_rows=12, cgra_columns=12),
            NeuraDemo.Kernel(kernel_name="gemm.c", kernel_id=0, arrive_period=3276800, unroll_factor=1, vector_factor=16, total_iterations=2097152, cgra_rows=12, cgra_columns=12),
            NeuraDemo.Kernel(kernel_name="relu+histogram.c", kernel_id=6, arrive_period=102400, unroll_factor=1, vector_factor=1, total_iterations=262144, cgra_rows=12, cgra_columns=12),
        ]
    ]

    taskCase5=[
        [
            NeuraDemo.Kernel(kernel_name="fir.cpp", kernel_id=7, arrive_period=163840, unroll_factor=1, vector_factor=16, total_iterations=2048, cgra_rows=4, cgra_columns=4),
            NeuraDemo.Kernel(kernel_name="latnrm.c", kernel_id=8, arrive_period=163840, unroll_factor=4, vector_factor=1, total_iterations=1280, cgra_rows=4, cgra_columns=4),
            NeuraDemo.Kernel(kernel_name="fft.c", kernel_id=2, arrive_period=163840, unroll_factor=2, vector_factor=1, total_iterations=112640, cgra_rows=4, cgra_columns=4),
            NeuraDemo.Kernel(kernel_name="dtw.cpp", kernel_id=4, arrive_period=665360, unroll_factor=1, vector_factor=16, total_iterations=16384, cgra_rows=4, cgra_columns=4),
            NeuraDemo.Kernel(kernel_name="spmv.c", kernel_id=3, arrive_period=665360, unroll_factor=4, vector_factor=1, total_iterations=65536, cgra_rows=4, cgra_columns=4),
            NeuraDemo.Kernel(kernel_name="conv.c", kernel_id=1, arrive_period=3276800, unroll_factor=4, vector_factor=1, total_iterations=655360, cgra_rows=4, cgra_columns=4),
            NeuraDemo.Kernel(kernel_name="mvt.c", kernel_id=5, arrive_period=102400, unroll_factor=4, vector_factor=1, total_iterations=16384, cgra_rows=4, cgra_columns=4),
            NeuraDemo.Kernel(kernel_name="gemm.c", kernel_id=0, arrive_period=3276800, unroll_factor=1, vector_factor=16, total_iterations=2097152, cgra_rows=4, cgra_columns=4),
            NeuraDemo.Kernel(kernel_name="relu+histogram.c", kernel_id=6, arrive_period=102400, unroll_factor=4, vector_factor=1, total_iterations=262144, cgra_rows=4, cgra_columns=4),
        ]
    ]
    NeuraDemo.run_multiple_simulations_and_save_to_csv(baselineCase5, "Baseline", priority_boosting = 0, kernel_case=5, num_cgras=1)  # one cgra is 12x12
    NeuraDemo.run_multiple_simulations_and_save_to_csv(taskCase5, "NoBosting", priority_boosting = 0, kernel_case=5, num_cgras=9)  # one cgra is 4x4
    NeuraDemo.run_multiple_simulations_and_save_to_csv(taskCase5, "BostingScalar", priority_boosting = 1, kernel_case=5, num_cgras=9) # one cgra is 4x4
    NeuraDemo.run_multiple_simulations_and_save_to_csv(taskCase5, "BostingScalarFuse", priority_boosting = 2, kernel_case=5, num_cgras=9)    # one cgra is 4x4
    NeuraDemo.run_multiple_simulations_and_save_to_csv(taskCase5, "BostingScalarFuseVector", priority_boosting = 3, kernel_case=5, num_cgras=9)    # one cgra is 4x4

elif args.old_new == 5:
    baselineCase7=[
        [
            NeuraDemo.Kernel(kernel_name="fir.cpp", kernel_id=7, arrive_period=163840, unroll_factor=1, vector_factor=16, total_iterations=2048, cgra_rows=12, cgra_columns=12),
            NeuraDemo.Kernel(kernel_name="latnrm.c", kernel_id=8, arrive_period=163840, unroll_factor=4, vector_factor=1, total_iterations=1280, cgra_rows=12, cgra_columns=12),
            NeuraDemo.Kernel(kernel_name="fft.c", kernel_id=2, arrive_period=163840, unroll_factor=1, vector_factor=1, total_iterations=112640, cgra_rows=12, cgra_columns=12),
            NeuraDemo.Kernel(kernel_name="dtw.cpp", kernel_id=4, arrive_period=665360, unroll_factor=1, vector_factor=16, total_iterations=16384, cgra_rows=12, cgra_columns=12),
            NeuraDemo.Kernel(kernel_name="spmv.c", kernel_id=3, arrive_period=665360, unroll_factor=2, vector_factor=1, total_iterations=65536, cgra_rows=12, cgra_columns=12),
            NeuraDemo.Kernel(kernel_name="conv.c", kernel_id=1, arrive_period=3276800, unroll_factor=4, vector_factor=1, total_iterations=655360, cgra_rows=12, cgra_columns=12),
            NeuraDemo.Kernel(kernel_name="mvt.c", kernel_id=5, arrive_period=163840, unroll_factor=4, vector_factor=1, total_iterations=16384, cgra_rows=12, cgra_columns=12),
            NeuraDemo.Kernel(kernel_name="gemm.c", kernel_id=0, arrive_period=3276800, unroll_factor=1, vector_factor=16, total_iterations=2097152, cgra_rows=12, cgra_columns=12),
            NeuraDemo.Kernel(kernel_name="relu+histogram.c", kernel_id=6, arrive_period=163840, unroll_factor=1, vector_factor=1, total_iterations=262144, cgra_rows=12, cgra_columns=12),
            #NeuraDemo.Kernel(kernel_name="relu+histogram.c", kernel_id=6, arrive_period=10960000, unroll_factor=1, vector_factor=1, total_iterations=4096, cgra_rows=12, cgra_columns=12)
        ]
    ]

    taskCase7=[
        [
            NeuraDemo.Kernel(kernel_name="fir.cpp", kernel_id=7, arrive_period=163840, unroll_factor=1, vector_factor=16, total_iterations=2048, cgra_rows=4, cgra_columns=4),
            NeuraDemo.Kernel(kernel_name="latnrm.c", kernel_id=8, arrive_period=163840, unroll_factor=4, vector_factor=1, total_iterations=1280, cgra_rows=4, cgra_columns=4),
            NeuraDemo.Kernel(kernel_name="fft.c", kernel_id=2, arrive_period=163840, unroll_factor=2, vector_factor=1, total_iterations=112640, cgra_rows=4, cgra_columns=4),
            NeuraDemo.Kernel(kernel_name="dtw.cpp", kernel_id=4, arrive_period=665360, unroll_factor=1, vector_factor=16, total_iterations=16384, cgra_rows=4, cgra_columns=4),
            NeuraDemo.Kernel(kernel_name="spmv.c", kernel_id=3, arrive_period=665360, unroll_factor=4, vector_factor=1, total_iterations=65536, cgra_rows=4, cgra_columns=4),
            NeuraDemo.Kernel(kernel_name="conv.c", kernel_id=1, arrive_period=3276800, unroll_factor=4, vector_factor=1, total_iterations=655360, cgra_rows=4, cgra_columns=4),
            NeuraDemo.Kernel(kernel_name="mvt.c", kernel_id=5, arrive_period=163840, unroll_factor=4, vector_factor=1, total_iterations=16384, cgra_rows=4, cgra_columns=4),
            NeuraDemo.Kernel(kernel_name="gemm.c", kernel_id=0, arrive_period=3276800, unroll_factor=1, vector_factor=16, total_iterations=2097152, cgra_rows=4, cgra_columns=4),
            NeuraDemo.Kernel(kernel_name="relu+histogram.c", kernel_id=6, arrive_period=163840, unroll_factor=4, vector_factor=1, total_iterations=262144, cgra_rows=4, cgra_columns=4),
            #NeuraDemo.Kernel(kernel_name="relu+histogram.c", kernel_id=6, arrive_period=10960000, unroll_factor=4, vector_factor=1, total_iterations=4096, cgra_rows=4, cgra_columns=4)
        ]
    ]
    # TODO： arrive_period decouple with execution time
    # TODO: case 1-6 + N
    NeuraDemo.run_multiple_simulations_and_save_to_csv(baselineCase7, "Baseline", priority_boosting = 0, kernel_case=8, num_cgras=1)  # one cgra is 12x12
    NeuraDemo.run_multiple_simulations_and_save_to_csv(taskCase7, "NoBosting", priority_boosting = 0, kernel_case=8, num_cgras=9)  # one cgra is 4x4
    NeuraDemo.run_multiple_simulations_and_save_to_csv(taskCase7, "BostingScalar", priority_boosting = 1, kernel_case=8, num_cgras=9) # one cgra is 4x4
    NeuraDemo.run_multiple_simulations_and_save_to_csv(taskCase7, "BostingScalarFuse", priority_boosting = 2, kernel_case=8, num_cgras=9)    # one cgra is 4x4
    NeuraDemo.run_multiple_simulations_and_save_to_csv(taskCase7, "BostingScalarFuseVector", priority_boosting = 3, kernel_case=8, num_cgras=9)    # one cgra is 4x4
elif args.old_new == 6:
    baselineCase6=[
        [
            NeuraDemo.Kernel(kernel_name="fir.cpp", kernel_id=7, arrive_period=204800, unroll_factor=1, vector_factor=16, total_iterations=2048, cgra_rows=12, cgra_columns=12),
            NeuraDemo.Kernel(kernel_name="latnrm.c", kernel_id=8, arrive_period=204800, unroll_factor=4, vector_factor=1, total_iterations=1280, cgra_rows=12, cgra_columns=12),
            NeuraDemo.Kernel(kernel_name="fft.c", kernel_id=2, arrive_period=204800, unroll_factor=1, vector_factor=16, total_iterations=112640, cgra_rows=12, cgra_columns=12),
            NeuraDemo.Kernel(kernel_name="dtw.cpp", kernel_id=4, arrive_period=819200, unroll_factor=1, vector_factor=16, total_iterations=16384, cgra_rows=12, cgra_columns=12),
            NeuraDemo.Kernel(kernel_name="spmv.c", kernel_id=3, arrive_period=819200, unroll_factor=2, vector_factor=1, total_iterations=65536, cgra_rows=12, cgra_columns=12),
            NeuraDemo.Kernel(kernel_name="conv.c", kernel_id=1, arrive_period=5242880, unroll_factor=4, vector_factor=1, total_iterations=655360, cgra_rows=12, cgra_columns=12),
            NeuraDemo.Kernel(kernel_name="mvt.c", kernel_id=5, arrive_period=204800, unroll_factor=4, vector_factor=1, total_iterations=16384, cgra_rows=12, cgra_columns=12),
            NeuraDemo.Kernel(kernel_name="gemm.c", kernel_id=0, arrive_period=5242880, unroll_factor=1, vector_factor=16, total_iterations=2097152, cgra_rows=12, cgra_columns=12),
            NeuraDemo.Kernel(kernel_name="relu+histogram.c", kernel_id=6, arrive_period=204800, unroll_factor=1, vector_factor=1, total_iterations=360000, cgra_rows=12, cgra_columns=12),
        ]
    ]

    taskCase6=[
        [
            NeuraDemo.Kernel(kernel_name="fir.cpp", kernel_id=7, arrive_period=204800, unroll_factor=1, vector_factor=16, total_iterations=2048, cgra_rows=4, cgra_columns=4),
            NeuraDemo.Kernel(kernel_name="latnrm.c", kernel_id=8, arrive_period=204800, unroll_factor=4, vector_factor=1, total_iterations=1280, cgra_rows=4, cgra_columns=4),
            NeuraDemo.Kernel(kernel_name="fft.c", kernel_id=2, arrive_period=204800, unroll_factor=1, vector_factor=16, total_iterations=112640, cgra_rows=4, cgra_columns=4),
            NeuraDemo.Kernel(kernel_name="dtw.cpp", kernel_id=4, arrive_period=819200, unroll_factor=1, vector_factor=16, total_iterations=16384, cgra_rows=4, cgra_columns=4),
            NeuraDemo.Kernel(kernel_name="spmv.c", kernel_id=3, arrive_period=819200, unroll_factor=4, vector_factor=1, total_iterations=65536, cgra_rows=4, cgra_columns=4),
            NeuraDemo.Kernel(kernel_name="conv.c", kernel_id=1, arrive_period=5242880, unroll_factor=4, vector_factor=1, total_iterations=655360, cgra_rows=4, cgra_columns=4),
            NeuraDemo.Kernel(kernel_name="mvt.c", kernel_id=5, arrive_period=204800, unroll_factor=4, vector_factor=1, total_iterations=16384, cgra_rows=4, cgra_columns=4),
            NeuraDemo.Kernel(kernel_name="gemm.c", kernel_id=0, arrive_period=5242880, unroll_factor=1, vector_factor=16, total_iterations=2097152, cgra_rows=4, cgra_columns=4),
            NeuraDemo.Kernel(kernel_name="relu+histogram.c", kernel_id=6, arrive_period=204800, unroll_factor=4, vector_factor=1, total_iterations=360000, cgra_rows=4, cgra_columns=4),
        ]
    ]

    NeuraDemo.run_multiple_simulations_and_save_to_csv(baselineCase6, "Baseline", priority_boosting = 0, kernel_case=6, num_cgras=1)  # one cgra is 12x12
    NeuraDemo.run_multiple_simulations_and_save_to_csv(taskCase6, "NoBosting", priority_boosting = 0, kernel_case=6, num_cgras=9)  # one cgra is 4x4
    NeuraDemo.run_multiple_simulations_and_save_to_csv(taskCase6, "BostingScalar", priority_boosting = 1, kernel_case=6, num_cgras=9) # one cgra is 4x4
    NeuraDemo.run_multiple_simulations_and_save_to_csv(taskCase6, "BostingScalarFuse", priority_boosting = 2, kernel_case=6, num_cgras=9)    # one cgra is 4x4
    NeuraDemo.run_multiple_simulations_and_save_to_csv(taskCase6, "BostingScalarFuseVector", priority_boosting = 3, kernel_case=6, num_cgras=9)    # one cgra is 4x4
elif args.old_new == 72:
    # TODO:8x8 下relu,spmv,conv的U和V为1
    baselineCase7=[
        [
            NeuraDemo.Kernel(kernel_name="fir.cpp", kernel_id=7, arrive_period=204800, unroll_factor=1, vector_factor=16, total_iterations=2048, cgra_rows=8, cgra_columns=8),
            NeuraDemo.Kernel(kernel_name="latnrm.c", kernel_id=8, arrive_period=204800, unroll_factor=4, vector_factor=1, total_iterations=1280, cgra_rows=8, cgra_columns=8),
            NeuraDemo.Kernel(kernel_name="fft.c", kernel_id=2, arrive_period=5242880, unroll_factor=1, vector_factor=16, total_iterations=112640, cgra_rows=8, cgra_columns=8),
            NeuraDemo.Kernel(kernel_name="dtw.cpp", kernel_id=4, arrive_period=665360, unroll_factor=1, vector_factor=16, total_iterations=16384, cgra_rows=8, cgra_columns=8),
            NeuraDemo.Kernel(kernel_name="spmv.c", kernel_id=3, arrive_period=665360, unroll_factor=1, vector_factor=1, total_iterations=65536, cgra_rows=8, cgra_columns=8),
            NeuraDemo.Kernel(kernel_name="conv.c", kernel_id=1, arrive_period=5242880, unroll_factor=1, vector_factor=1, total_iterations=655360, cgra_rows=8, cgra_columns=8),
            NeuraDemo.Kernel(kernel_name="mvt.c", kernel_id=5, arrive_period=204800, unroll_factor=4, vector_factor=1, total_iterations=16384, cgra_rows=8, cgra_columns=8),
            NeuraDemo.Kernel(kernel_name="gemm.c", kernel_id=0, arrive_period=5242880, unroll_factor=1, vector_factor=16, total_iterations=2097152, cgra_rows=8, cgra_columns=8),
            NeuraDemo.Kernel(kernel_name="relu+histogram.c", kernel_id=6, arrive_period=204800, unroll_factor=1, vector_factor=1, total_iterations=262144, cgra_rows=8, cgra_columns=8),
            #NeuraDemo.Kernel(kernel_name="relu+histogram.c", kernel_id=6, arrive_period=10960000, unroll_factor=1, vector_factor=1, total_iterations=4096, cgra_rows=8, cgra_columns=8)
        ]
    ]

    taskCase7=[
        [
            NeuraDemo.Kernel(kernel_name="fir.cpp", kernel_id=7, arrive_period=204800, unroll_factor=1, vector_factor=16, total_iterations=2048, cgra_rows=4, cgra_columns=4),
            NeuraDemo.Kernel(kernel_name="latnrm.c", kernel_id=8, arrive_period=204800, unroll_factor=4, vector_factor=1, total_iterations=1280, cgra_rows=4, cgra_columns=4),
            NeuraDemo.Kernel(kernel_name="fft.c", kernel_id=2, arrive_period=5242880, unroll_factor=1, vector_factor=16, total_iterations=112640, cgra_rows=4, cgra_columns=4),
            NeuraDemo.Kernel(kernel_name="dtw.cpp", kernel_id=4, arrive_period=665360, unroll_factor=1, vector_factor=16, total_iterations=16384, cgra_rows=4, cgra_columns=4),
            NeuraDemo.Kernel(kernel_name="spmv.c", kernel_id=3, arrive_period=665360, unroll_factor=4, vector_factor=1, total_iterations=65536, cgra_rows=4, cgra_columns=4),
            NeuraDemo.Kernel(kernel_name="conv.c", kernel_id=1, arrive_period=5242880, unroll_factor=4, vector_factor=1, total_iterations=655360, cgra_rows=4, cgra_columns=4),
            NeuraDemo.Kernel(kernel_name="mvt.c", kernel_id=5, arrive_period=204800, unroll_factor=4, vector_factor=1, total_iterations=16384, cgra_rows=4, cgra_columns=4),
            NeuraDemo.Kernel(kernel_name="gemm.c", kernel_id=0, arrive_period=5242880, unroll_factor=1, vector_factor=16, total_iterations=2097152, cgra_rows=4, cgra_columns=4),
            NeuraDemo.Kernel(kernel_name="relu+histogram.c", kernel_id=6, arrive_period=204800, unroll_factor=4, vector_factor=1, total_iterations=262144, cgra_rows=4, cgra_columns=4),
            #NeuraDemo.Kernel(kernel_name="relu+histogram.c", kernel_id=6, arrive_period=10960000, unroll_factor=4, vector_factor=1, total_iterations=4096, cgra_rows=4, cgra_columns=4)
        ]
    ]
    NeuraDemo.run_multiple_simulations_and_save_to_csv(baselineCase7, "Baseline", priority_boosting = 0, kernel_case=72, num_cgras=1)  # one cgra is 8x8
    NeuraDemo.run_multiple_simulations_and_save_to_csv(taskCase7, "NoBosting", priority_boosting = 0, kernel_case=72, num_cgras=4)  # one cgra is 4x4
    NeuraDemo.run_multiple_simulations_and_save_to_csv(taskCase7, "BostingScalar", priority_boosting = 1, kernel_case=72, num_cgras=4) # one cgra is 4x4
    NeuraDemo.run_multiple_simulations_and_save_to_csv(taskCase7, "BostingScalarFuse", priority_boosting = 2, kernel_case=72, num_cgras=4)    # one cgra is 4x4
    NeuraDemo.run_multiple_simulations_and_save_to_csv(taskCase7, "BostingScalarFuseVector", priority_boosting = 3, kernel_case=72, num_cgras=4)    # one cgra is 4x4
elif args.old_new == 74:
    baselineCase74=[
            [
                NeuraDemo.Kernel(kernel_name="fir.cpp", kernel_id=7, arrive_period=204800, unroll_factor=1, vector_factor=16, total_iterations=2048, cgra_rows=16, cgra_columns=16),
                NeuraDemo.Kernel(kernel_name="latnrm.c", kernel_id=8, arrive_period=204800, unroll_factor=4, vector_factor=1, total_iterations=1280, cgra_rows=16, cgra_columns=16),
                NeuraDemo.Kernel(kernel_name="fft.c", kernel_id=2, arrive_period=5242880, unroll_factor=1, vector_factor=16, total_iterations=112640, cgra_rows=16, cgra_columns=16),
                NeuraDemo.Kernel(kernel_name="dtw.cpp", kernel_id=4, arrive_period=665360, unroll_factor=1, vector_factor=16, total_iterations=16384, cgra_rows=16, cgra_columns=16),
                NeuraDemo.Kernel(kernel_name="spmv.c", kernel_id=3, arrive_period=665360, unroll_factor=4, vector_factor=1, total_iterations=65536, cgra_rows=16, cgra_columns=16),
                NeuraDemo.Kernel(kernel_name="conv.c", kernel_id=1, arrive_period=5242880, unroll_factor=4, vector_factor=1, total_iterations=655360, cgra_rows=16, cgra_columns=16),
                NeuraDemo.Kernel(kernel_name="mvt.c", kernel_id=5, arrive_period=204800, unroll_factor=4, vector_factor=1, total_iterations=16384, cgra_rows=16, cgra_columns=16),
                NeuraDemo.Kernel(kernel_name="gemm.c", kernel_id=0, arrive_period=5242880, unroll_factor=1, vector_factor=16, total_iterations=2097152, cgra_rows=16, cgra_columns=16),
                NeuraDemo.Kernel(kernel_name="relu+histogram.c", kernel_id=6, arrive_period=204800, unroll_factor=4, vector_factor=1, total_iterations=262144, cgra_rows=16, cgra_columns=16),
            ]
    ]

    taskCase74=[
            [
                NeuraDemo.Kernel(kernel_name="fir.cpp", kernel_id=7, arrive_period=204800, unroll_factor=1, vector_factor=16, total_iterations=2048, cgra_rows=4, cgra_columns=4),
                NeuraDemo.Kernel(kernel_name="latnrm.c", kernel_id=8, arrive_period=204800, unroll_factor=4, vector_factor=1, total_iterations=1280, cgra_rows=4, cgra_columns=4),
                NeuraDemo.Kernel(kernel_name="fft.c", kernel_id=2, arrive_period=5242880, unroll_factor=1, vector_factor=16, total_iterations=112640, cgra_rows=4, cgra_columns=4),
                NeuraDemo.Kernel(kernel_name="dtw.cpp", kernel_id=4, arrive_period=665360, unroll_factor=1, vector_factor=16, total_iterations=16384, cgra_rows=4, cgra_columns=4),
                NeuraDemo.Kernel(kernel_name="spmv.c", kernel_id=3, arrive_period=665360, unroll_factor=4, vector_factor=1, total_iterations=65536, cgra_rows=4, cgra_columns=4),
                NeuraDemo.Kernel(kernel_name="conv.c", kernel_id=1, arrive_period=5242880, unroll_factor=4, vector_factor=1, total_iterations=655360, cgra_rows=4, cgra_columns=4),
                NeuraDemo.Kernel(kernel_name="mvt.c", kernel_id=5, arrive_period=204800, unroll_factor=4, vector_factor=1, total_iterations=16384, cgra_rows=4, cgra_columns=4),
                NeuraDemo.Kernel(kernel_name="gemm.c", kernel_id=0, arrive_period=5242880, unroll_factor=1, vector_factor=16, total_iterations=2097152, cgra_rows=4, cgra_columns=4),
                NeuraDemo.Kernel(kernel_name="relu+histogram.c", kernel_id=6, arrive_period=204800, unroll_factor=4, vector_factor=1, total_iterations=262144, cgra_rows=4, cgra_columns=4),
            ]
    ]


    NeuraDemo.run_multiple_simulations_and_save_to_csv(baselineCase74, "Baseline", priority_boosting = 0, kernel_case=74, num_cgras=1)  # one cgra is 16x16
    NeuraDemo.run_multiple_simulations_and_save_to_csv(taskCase74, "NoBosting", priority_boosting = 0, kernel_case=74, num_cgras=16)  # one cgra is 4x4
    NeuraDemo.run_multiple_simulations_and_save_to_csv(taskCase74, "BostingScalar", priority_boosting = 1, kernel_case=74, num_cgras=16) # one cgra is 4x4
    NeuraDemo.run_multiple_simulations_and_save_to_csv(taskCase74, "BostingScalarFuse", priority_boosting = 2, kernel_case=74, num_cgras=16)    # one cgra is 4x4
    NeuraDemo.run_multiple_simulations_and_save_to_csv(taskCase74, "BostingScalarFuseVector", priority_boosting = 3, kernel_case=74, num_cgras=16)    # one cgra is 4x4
elif args.old_new == 75:

    baselineCase75=[
            [
                NeuraDemo.Kernel(kernel_name="fir.cpp", kernel_id=7, arrive_period=204800, unroll_factor=1, vector_factor=16, total_iterations=2048, cgra_rows=20, cgra_columns=20),
                NeuraDemo.Kernel(kernel_name="latnrm.c", kernel_id=8, arrive_period=204800, unroll_factor=4, vector_factor=1, total_iterations=1280, cgra_rows=20, cgra_columns=20),
                NeuraDemo.Kernel(kernel_name="fft.c", kernel_id=2, arrive_period=5242880, unroll_factor=1, vector_factor=16, total_iterations=112640, cgra_rows=20, cgra_columns=20),
                NeuraDemo.Kernel(kernel_name="dtw.cpp", kernel_id=4, arrive_period=665360, unroll_factor=1, vector_factor=16, total_iterations=16384, cgra_rows=20, cgra_columns=20),
                NeuraDemo.Kernel(kernel_name="spmv.c", kernel_id=3, arrive_period=665360, unroll_factor=4, vector_factor=1, total_iterations=65536, cgra_rows=20, cgra_columns=20),
                NeuraDemo.Kernel(kernel_name="conv.c", kernel_id=1, arrive_period=5242880, unroll_factor=4, vector_factor=1, total_iterations=655360, cgra_rows=20, cgra_columns=20),
                NeuraDemo.Kernel(kernel_name="mvt.c", kernel_id=5, arrive_period=204800, unroll_factor=4, vector_factor=1, total_iterations=16384, cgra_rows=20, cgra_columns=20),
                NeuraDemo.Kernel(kernel_name="gemm.c", kernel_id=0, arrive_period=5242880, unroll_factor=1, vector_factor=16, total_iterations=2097152, cgra_rows=20, cgra_columns=20),
                NeuraDemo.Kernel(kernel_name="relu+histogram.c", kernel_id=6, arrive_period=204800, unroll_factor=4, vector_factor=1, total_iterations=262144, cgra_rows=20, cgra_columns=20),
            ]
    ]

    taskCase75=[
            [
                NeuraDemo.Kernel(kernel_name="fir.cpp", kernel_id=7, arrive_period=204800, unroll_factor=1, vector_factor=16, total_iterations=2048, cgra_rows=4, cgra_columns=4),
                NeuraDemo.Kernel(kernel_name="latnrm.c", kernel_id=8, arrive_period=204800, unroll_factor=4, vector_factor=1, total_iterations=1280, cgra_rows=4, cgra_columns=4),
                NeuraDemo.Kernel(kernel_name="fft.c", kernel_id=2, arrive_period=5242880, unroll_factor=1, vector_factor=16, total_iterations=112640, cgra_rows=4, cgra_columns=4),
                NeuraDemo.Kernel(kernel_name="dtw.cpp", kernel_id=4, arrive_period=665360, unroll_factor=1, vector_factor=16, total_iterations=16384, cgra_rows=4, cgra_columns=4),
                NeuraDemo.Kernel(kernel_name="spmv.c", kernel_id=3, arrive_period=665360, unroll_factor=4, vector_factor=1, total_iterations=65536, cgra_rows=4, cgra_columns=4),
                NeuraDemo.Kernel(kernel_name="conv.c", kernel_id=1, arrive_period=5242880, unroll_factor=4, vector_factor=1, total_iterations=655360, cgra_rows=4, cgra_columns=4),
                NeuraDemo.Kernel(kernel_name="mvt.c", kernel_id=5, arrive_period=204800, unroll_factor=4, vector_factor=1, total_iterations=16384, cgra_rows=4, cgra_columns=4),
                NeuraDemo.Kernel(kernel_name="gemm.c", kernel_id=0, arrive_period=5242880, unroll_factor=1, vector_factor=16, total_iterations=2097152, cgra_rows=4, cgra_columns=4),
                NeuraDemo.Kernel(kernel_name="relu+histogram.c", kernel_id=6, arrive_period=204800, unroll_factor=4, vector_factor=1, total_iterations=262144, cgra_rows=4, cgra_columns=4),
            ]
    ]
    NeuraDemo.run_multiple_simulations_and_save_to_csv(baselineCase75, "Baseline", priority_boosting = 0, kernel_case=75, num_cgras=1)  # one cgra is 20x20
    NeuraDemo.run_multiple_simulations_and_save_to_csv(taskCase75, "NoBosting", priority_boosting = 0, kernel_case=75, num_cgras=25)  # one cgra is 4x4
    NeuraDemo.run_multiple_simulations_and_save_to_csv(taskCase75, "BostingScalar", priority_boosting = 1, kernel_case=75, num_cgras=25) # one cgra is 4x4
    NeuraDemo.run_multiple_simulations_and_save_to_csv(taskCase75, "BostingScalarFuse", priority_boosting = 2, kernel_case=75, num_cgras=25)    # one cgra is 4x4
    NeuraDemo.run_multiple_simulations_and_save_to_csv(taskCase75, "BostingScalarFuseVector", priority_boosting = 3, kernel_case=75, num_cgras=25)    # one cgra is 4x4
