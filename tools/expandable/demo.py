def simulate(num_cgras, kernels, priority_boosting, lcm_time=26214400):
    """
    lcm_time=26214400
    Simulate the execution of multiple kernels on a CGRA architecture.

    Parameters:
        num_cgras (int): The number of CGRAs in the CGRA architecture.
        kernels (list of Kernel): The list of kernels to simulate.
        priority_boosting (bool): Whether to enable priority boosting.
        lcm_time (int): The least common multiple of the arrival periods.

    Returns:
        dict: A dictionary that maps kernel names to their total latencies.
    """
    # 添加目标检查时间
    CHECK_TIME = 26271744
    # 标记是否已输出结果，避免重复输出
    checked = False

    available_cgras = num_cgras
    events = []  # when a kernel arrives or ends, it is an event
    current_time = 0
    waiting_instances = []
    running_instances = []
    completed_instances = []
    runned_kernel_names = []
    # Dictionary to store per-kernel arrival times
    kernel_arrival_count = {kernel.kernel_id: 0 for kernel in kernels}
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
    # TODO：从函数名换成函数ID
    arrive_times_list = {
        kernel.kernel_id: ((lcm_time // kernel.arrive_period))  # TODO: +1
        for kernel in kernels
    }
    print(arrive_times_list)


    print(f"\033[91mPriority Boosting Level: {priority_boosting}\033[0m")

    for kernel in kernels:
        print(f"Kernel {kernel.kernel_name} base_ii={kernel.base_ii}, expandable_ii={kernel.expandable_ii}, \
              iterations={kernel.total_iterations}, utilization={kernel.utilization}, arrive_times, {arrive_times_list[kernel.kernel_id]}")

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
        idle_tracker.check_idle_period(current_time, available_cgras, waiting_instances)
        print(f"Processing event at time {current_time}: type={event_type}, kernel={kernel_or_instance.kernel_name if event_type == 'arrival' else kernel_or_instance.kernel.kernel_name}")

        if event_type == 'arrival':
            kernel = kernel_or_instance
            kernel_arrival_count[kernel.kernel_id] += 1
            # Create a new instance
            instance = kernel.create_instance(current_time)
            # Schedule next arrival if within lcm_time
            next_arrival = current_time + kernel.arrive_period
            if kernel_arrival_count[kernel.kernel_id] < arrive_times_list[kernel.kernel_id]:
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

        # 检查是否达到目标时间，未输出过结果，且当前时间 >= 目标时间
        if not checked and current_time >= CHECK_TIME:
            print(f"\n=== At time {CHECK_TIME}, number of completed functions: {len(completed_instances)} ===")
            checked = True  # 标记已输出，避免重复

        print("="*20)

    # 如果整个模拟结束都没达到目标时间，也输出结果
    if not checked:
        print(f"\n=== Simulation ended before {CHECK_TIME}, number of completed functions: {len(completed_instances)} ===")

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
    waiting_time_nolap = idle_tracker.total_waiting_time_nolap
    overall_latency = current_time  # when all kernels are done

    print(f"Simulation completed. Kernel latencies: {kernel_latency}")
    print(f"Kernel execution_ratio: {kernel_execution_ratio}")
    print(f"Kernel execution duration distributions: {kernel_execution_distribution}")
    print(f"Kernel Runned List: {runned_kernel_names}")
    print(f"CGRA utilization: {cgra_utilization}")
    print(f"overall latency: {overall_latency}")
    print(f"overall execution: {overall_execution}")
    print(f"overall waiting_time_nolap: {waiting_time_nolap}")
    return kernel_latency, kernel_waiting_distribution, kernel_execution_ratio, kernel_waiting_ratio, kernel_execution_distribution, cgra_utilization, overall_latency, overall_execution