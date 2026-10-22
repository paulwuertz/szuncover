from calltree import ThreadStats, deepest_call_tree


def print_stack_size_report(fn_callee_map, config):
    overflows = False
    print("┌" + 78 * "─" + "┐")
    threadStats = {}
    for thread in config.threads:
        thread_fn_name = thread.thread_entry_name
        thread_stack_size = thread.stack_size
        if thread_fn_name in fn_callee_map:
            fn_node = fn_callee_map[thread_fn_name]
            stats = ThreadStats(unresolved_calls={}, missing_stack_sizes=[])
            thread_calltree = deepest_call_tree(fn_node, fn_callee_map, stats)
            threadStats[thread_fn_name] = stats
            worst_stack_size = thread_calltree[0]
            # stack_report = stack_report[function_name]
            stack_use_percent = worst_stack_size / thread_stack_size * 100
            progressbar_20_full = int(stack_use_percent / 100.0 * 20)
            progressbar_20_empty = 20 - progressbar_20_full
            # │ log_process_thread_func   - 100.0% - 11111/22222 - │███████████████-----│
            print(
                f"│ {thread_fn_name:<30} - ({f'{stack_use_percent:.1f}':>5}%) {worst_stack_size:>6}"
                f"/{thread_stack_size:>6} │{progressbar_20_full * '█'}{progressbar_20_empty * '-'}│"
            )
        else:
            print(f"│ {thread_fn_name:<30} - (function not found in build artifacts)     │")
    print("└" + 78 * "─" + "┘")

    print("WARNING: Given calltree info may limit this analysis: ")
    print("* number of functions with unresolved calls in thread:")
    for thread_fn_name, stats in threadStats.items():
        total_calls_to_unresolved_all_calls = sum(stats.unresolved_calls.values())
        print(
            "\t* %s: %d resulting in %d missing calls in the calltree",
            thread_fn_name,
            len(stats.unresolved_calls),
            total_calls_to_unresolved_all_calls,
        )
    print("* number of functions with missing stacksize in calltree:")
    for thread_fn_name, stats in threadStats.items():
        print("\t* ", thread_fn_name, ": ", len(stats.missing_stack_sizes))

    if overflows:
        sys.exit(1)
