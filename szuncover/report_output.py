import logging
import sys
from dataclasses import dataclass

from szuncover.calltree import (
    MissingStats,
    ThreadStats,
    deepest_call_tree,
    get_total_missings,
    reset_node_visits,
)
from szuncover.config import SZuncoverConfig
from szuncover.gcc_vcg_parser import FunctionCalleeEntry

logger = logging.getLogger()


@dataclass
class CallGraphReport:
    threads: list[ThreadStats]
    has_overflows: bool = False


def get_report(fn_callee_map: dict[str, FunctionCalleeEntry], config: SZuncoverConfig):
    report = CallGraphReport(threads=[])
    for conf_thread_entry in config.threads:
        thread_name = conf_thread_entry.thread_entry_name
        thread_stack_size = conf_thread_entry.stack_size
        stats = MissingStats(unresolved_calls={}, missing_stack_sizes=set(), missing_calls=[])
        threadstats = ThreadStats(config=conf_thread_entry, errors=stats)
        # reset to get correct stats for each thread
        reset_node_visits(fn_callee_map)

        if thread_name in fn_callee_map:
            threadstats.root = fn_callee_map[thread_name]
            worst_stack_size, threadstats.max_stack_call_path = deepest_call_tree(
                threadstats.root, fn_callee_map, stats
            )
            if worst_stack_size >= thread_stack_size:
                threadstats.has_overflows = report.has_overflows = True
            threadstats.stack_use_percent = worst_stack_size / thread_stack_size * 100
        report.threads += [threadstats]
    return report


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
    logger.info("┌" + 78 * "─" + "┐")
    report = get_report(fn_callee_map, config)
    for thread in report.threads:
        thread_fn_name = thread.config.thread_entry_name
        if thread.root:
            progressbar_20_full = int(thread.stack_use_percent / 100.0 * 20)
            progressbar_20_empty = 20 - progressbar_20_full
            # │ log_process_thread_func   - 100.0% - 11111/22222 - │███████████████-----│
            logger.info(
                f"│ {thread_fn_name:<30} - ({f'{thread.stack_use_percent:.1f}':>5}%) {thread.root.worst_stack_use:>6}"
                f"/{thread.config.stack_size:>6} │{progressbar_20_full * '█'}{progressbar_20_empty * '-'}│"
            )
        else:
            logger.info(f"│ {thread_fn_name:<30} - (function not found in build artifacts)     │")
    logger.info("└" + 78 * "─" + "┘")

    logger.warning("WARNING: Given calltree info may limit this analysis: ")
    logger.warning("* number of functions with unresolved calls in thread:")
    for thread in report.threads:
        total_calls_to_unresolved_all_calls = sum(thread.errors.unresolved_calls.values())
        logger.warning(
            f"\t* {thread.config.thread_entry_name}: {len(thread.errors.unresolved_calls)} resulting in "
            f"{total_calls_to_unresolved_all_calls} missing calls in the calltree"
        )
    logger.warning("* number of functions with missing stacksize in calltree:")
    for thread in report.threads:
        logger.warning(f"\t* {thread.config.thread_entry_name}: {len(thread.errors.missing_stack_sizes)}")

    if report.has_overflows:
        sys.exit(1)


def print_markdown_stack_size_report(fn_callee_map: dict[str, FunctionCalleeEntry], config: SZuncoverConfig):
    report = get_report(fn_callee_map, config)
    logger.info("## Stack check\n\n")
    logger.info("### Stack usage summary\n\n")
    logger.info("| Thread name | Max Stack Use | Usage % | Unresolved calls | Missing stacksizes |")
    logger.info("| ----------- | ----------- | ----------- | ----------- | ----------- |")
    for thread in report.threads:
        thread_fn_name = thread.config.thread_entry_name
        if thread.root:
            logger.info(
                "| %s | %d | %3.1f %% | %d | %d |",
                thread_fn_name,
                thread.root.worst_stack_use,
                thread.stack_use_percent,
                len(thread.errors.unresolved_calls),
                len(thread.errors.missing_stack_sizes),
            )
        else:
            logger.info(f"| {thread_fn_name:<30} | (function not | found in | build artifacts)   |")

    logger.info("\n### Stack usage details - worst cases found\n")
    for thread in report.threads:
        if not thread.root:
            continue
        note_type = "caution" if thread.has_overflows else "warning"
        stack_sum, stackliststr = 0, "Calltree\n\n"
        for c in thread.max_stack_call_path:
            stack_size = c.node.label.stack_size or 0
            stack_sum += stack_size
            stackliststr = stackliststr + f"* {c.title} StackSize: {stack_sum} bytes (Sum: {stack_sum})\n"
        threadWarningHeader = f"Worst Calltree for {thread.config.thread_entry_name}"
        threadWarningSummary = f"Is {len(thread.max_stack_call_path)} calls deep, expand for details."
        warningDetails = print_md_collapsible_msg_with_details(
            note_type, threadWarningHeader, threadWarningSummary, stackliststr
        )
        logger.info(warningDetails)

    logger.info("### Missing information\n\n")
    for thread in report.threads:
        logger.info(
            f"* {thread.config.thread_entry_name} at least {sum(thread.errors.unresolved_calls.values())} dynamic calls in "
            f"{len(thread.errors.unresolved_calls.keys())} functions left to resolve. {len(thread.errors.missing_stack_sizes)} functions with missing stack sizes."
        )

    stats = get_total_missings(fn_callee_map)
    totalNrDynamicCalls = sum(stats.unresolved_calls.values())
    nrFunctionsWithDynamicCalls = len(stats.unresolved_calls)
    nrFunctionsWithoutStackSize = len(stats.missing_stack_sizes)
    nrFunctionsWithMissingCalls = len(stats.missing_calls)  # TODO zero...
    nrCalls = sum(len(f.edges) for f in fn_callee_map.values())

    # totalNrResolvedCalls TODO not just count configured but successfully mapped calls
    print("\n**Consider adding or extending a config and add unresolved calls for better results**")
    print(f"\nThere are in {len(fn_callee_map)} functions and {nrCalls} calls at least:\n")
    print(f"* {totalNrDynamicCalls} dynamic calls in {nrFunctionsWithDynamicCalls} functions")
    print(f"* {nrFunctionsWithoutStackSize} functions without stacksize (often from linked libraries)")
    print(f"* {nrFunctionsWithMissingCalls} function calls which could not be found")
    # TODO %d dynamic calls are already resolved.\n"
    print("\n**Note**: The number of dynamic calls might be higher then the number of dynamic branch instructions.")
    print("      Like in a workqueue a single dynamic branch can execute more then on work tasks.")

    missingWarnSummary = "Expand to see all functions in detail"
    fnStackMissingWarnBody = "\n* " + "\n* ".join(stats.missing_stack_sizes)
    fnStackMissingWarning = print_md_collapsible_msg_with_details(
        "warning", "Missing stacksizes", missingWarnSummary, fnStackMissingWarnBody
    )
    logger.info(fnStackMissingWarning)

    missingCallsWarnBody = "\n* " + "\n* ".join(call[0] + " -> " + call[1] for call in stats.missing_calls)
    missingCallsWarning = print_md_collapsible_msg_with_details(
        "warning", "Unmatched calls", missingWarnSummary, missingCallsWarnBody
    )
    logger.info(missingCallsWarning)

    fnUnresolvedWarnBody = "\n* " + "\n* ".join(
        f + " has " + str(x) + " dynamic calls" for f, x in stats.unresolved_calls.items()
    )
    fnStackMissingWarning = print_md_collapsible_msg_with_details(
        "warning", "Dynamic calls", missingWarnSummary, fnUnresolvedWarnBody
    )
    logger.info(fnStackMissingWarning)

    if report.has_overflows:
        sys.exit(1)
