import logging
import sys

from szuncover.calltree import (
    MissingStats,
    deepest_call_tree,
    get_total_missings,
    reset_node_visits,
)
from szuncover.config import SZuncoverConfig
from szuncover.gcc_vcg_parser import FunctionCalleeEntry

logger = logging.getLogger()


def print_md_collapsible_msg_with_details(msgType, summaryHeader, summaryMsg, msgBody: str):
    return f"""

>>> [!{msgType}] {summaryHeader}

<details>
<summary>

{summaryMsg}

</summary>

{msgBody}

</details>

>>>

"""


def print_stack_size_report(fn_callee_map: dict[str, FunctionCalleeEntry], config: SZuncoverConfig):
    has_overflows = False
    logger.info("┌" + 78 * "─" + "┐")
    threadStats = {}
    for thread in config.threads:
        thread_fn_name = thread.thread_entry_name
        thread_stack_size = thread.stack_size
        # reset to get correct stats for each thread
        reset_node_visits(fn_callee_map)
        if thread_fn_name in fn_callee_map:
            fn_node = fn_callee_map[thread_fn_name]
            stats = MissingStats(unresolved_calls={}, missing_stack_sizes=set(), missing_calls=[])
            thread_calltree = deepest_call_tree(fn_node, fn_callee_map, stats)
            threadStats[thread_fn_name] = stats
            worst_stack_size = thread_calltree[0]
            if worst_stack_size >= thread_stack_size:
                has_overflows = True
            stack_use_percent = worst_stack_size / thread_stack_size * 100
            progressbar_20_full = int(stack_use_percent / 100.0 * 20)
            progressbar_20_empty = 20 - progressbar_20_full
            # │ log_process_thread_func   - 100.0% - 11111/22222 - │███████████████-----│
            logger.info(
                f"│ {thread_fn_name:<30} - ({f'{stack_use_percent:.1f}':>5}%) {worst_stack_size:>6}"
                f"/{thread_stack_size:>6} │{progressbar_20_full * '█'}{progressbar_20_empty * '-'}│"
            )
        else:
            logger.info(f"│ {thread_fn_name:<30} - (function not found in build artifacts)     │")
    logger.info("└" + 78 * "─" + "┘")

    logger.warning("WARNING: Given calltree info may limit this analysis: ")
    logger.warning("* number of functions with unresolved calls in thread:")
    for thread_fn_name, stats in threadStats.items():
        total_calls_to_unresolved_all_calls = sum(stats.unresolved_calls.values())
        logger.warning(
            f"\t* {thread_fn_name}: {len(stats.unresolved_calls)} resulting in {total_calls_to_unresolved_all_calls} missing calls in the calltree"
        )
    logger.warning("* number of functions with missing stacksize in calltree:")
    for thread_fn_name, stats in threadStats.items():
        logger.warning(f"\t* {thread_fn_name}: {len(stats.missing_stack_sizes)}")

    if has_overflows:
        sys.exit(1)


def print_markdown_stack_size_report(fn_callee_map: dict[str, FunctionCalleeEntry], config: SZuncoverConfig):
    has_overflows = False
    logger.info("## Stack check\n\n")
    logger.info("### Stack usage summary\n\n")
    threadInfos = {}
    logger.info("| Thread name | Max Stack Use | Usage %% | Unresolved calls | Missing stacksizes |")
    logger.info("| ----------- | ----------- | ----------- | ----------- | ----------- |")
    for conf_thread_entry in config.threads:
        thread_name, thread_stack_size = (
            conf_thread_entry.thread_entry_name,
            conf_thread_entry.stack_size,
        )

        if thread_name in fn_callee_map:
            fn_node = fn_callee_map[thread_name]
            stats = MissingStats(unresolved_calls={}, missing_stack_sizes=set(), missing_calls=[])
            worst_stack_size, thread_worst_calltree = deepest_call_tree(fn_node, fn_callee_map, stats)
            threadInfos[thread_name] = (
                thread_worst_calltree,
                worst_stack_size,
                stats,
                conf_thread_entry,
            )
            if worst_stack_size >= thread_stack_size:
                has_overflows = True
            stack_use_percent = worst_stack_size / thread_stack_size * 100
            logger.info(
                "| %s | %d | %3.1f %% | %d | %d |",
                thread_name,
                worst_stack_size,
                stack_use_percent,
                len(stats.unresolved_calls),
                len(stats.missing_stack_sizes),
            )
        else:
            logger.info(f"| {thread_name:<30} | (function not | found in | build artifacts)   |")

    logger.info("\n### Stack usage details - worst cases found\n")
    for thread_name, threadInfo in threadInfos.items():
        thread_worst_calltree, worst_stack_size, stats, conf_thread_entry = threadInfo
        is_overflow = worst_stack_size > conf_thread_entry.stack_size
        note_type = "caution"
        if is_overflow:
            note_type = "warning"
        stack_sum = 0
        stackliststr = "Calltree\n\n"
        for c in thread_worst_calltree:
            stack_size = c.node.label.stack_size or 0
            stack_sum += stack_size
            stackliststr = stackliststr + f"* {c.title} StackSize: {stack_sum} bytes (Sum: {stack_sum})\n"
        threadWarningHeader = f"Worst Calltree for {thread_name}"
        threadWarningSummary = f"Is {len(thread_worst_calltree)} calls deep, expand for details."
        warningDetails = print_md_collapsible_msg_with_details(
            note_type, threadWarningHeader, threadWarningSummary, stackliststr
        )
        logger.info(warningDetails)

    logger.info("### Missing information\n\n")
    for thread_name, threadInfo in threadInfos.items():
        thread_worst_calltree, worst_stack_size, stats, conf_thread_entry = threadInfo
        logger.info(
            f"* {thread_name} at least {sum(stats.unresolved_calls.values())} dynamic calls in {len(stats.unresolved_calls.keys())} functions left to resolve. {len(stats.missing_stack_sizes)} functions with missing stack sizes."
        )

    stats = get_total_missings(fn_callee_map)
    totalNrDynamicCalls = sum(stats.unresolved_calls.values())
    nrFunctionsWithDynamicCalls = len(stats.unresolved_calls)
    nrFunctionsWithoutStackSize = len(stats.missing_stack_sizes)
    nrFunctionsWithMissingCalls = len(stats.missing_calls)  # TODO zero...
    nrCalls = sum(len(f.edges) for f in fn_callee_map.values())

    # totalNrResolvedCalls TODO not just count configured but successfully mapped calls
    print("\n**Consider adding or extending a config and add unresolved calls for better results**")
    print(
        f"\nThere are in {len(fn_callee_map)} functions and {nrCalls} calls at least:\n\n* {totalNrDynamicCalls} dynamic calls in {nrFunctionsWithDynamicCalls} functions left to resolve"
    )
    print(f"* {nrFunctionsWithoutStackSize} functions without stacksize (ofen from linked libraries)")
    print(f"* {nrFunctionsWithMissingCalls} function calls which could not be found")
    # %d dynamic calls are already resolved.\n"
    print(
        "\n**Note**: The actual number of dynamic calls might be higher then the number of dynamic branch instructions."
    )
    print("      Like in a workqueue a single dynamic branch can execute more then on work tasks.")

    if has_overflows:
        sys.exit(1)
