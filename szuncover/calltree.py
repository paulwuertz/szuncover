import fnmatch
import logging
import os
from dataclasses import dataclass

from szuncover.gcc_vcg_parser import (
    GCC_INDIRECT_CALL_LABEL,
    FunctionCalleeEntry,
    VCG_Edge,
    VCG_Graph,
    VCG_Parser,
)

NO_WORST_STACK_SIZE_YET = -1

logger = logging.getLogger()


@dataclass
class ThreadStats:
    unresolved_calls: dict[str, int]
    missing_stack_sizes: list[str]


def find_files_with_extension(extension: str, top: str):
    for path, dirlist, filelist in os.walk(top):
        for name in fnmatch.filter(filelist, extension):
            yield os.path.join(path, name)


def get_vcg_graphs_from_build_dir(build_dir: str) -> list[VCG_Graph]:
    # print("parsing callgraph starting at %s" % build_dir)
    vcg_graphs = []
    call_files = find_files_with_extension("*.ci", build_dir)

    for ci_file in call_files:
        with open(ci_file) as file:
            ci_file_content = file.read()
            vcg_graph = VCG_Parser.parse_vcg_graph(ci_file_content)
            vcg_graphs += [vcg_graph]

    return vcg_graphs


def get_all_edges_from_vcg_graphs(vcg_graphs: list[VCG_Graph]) -> list[VCG_Edge]:
    all_edges = []
    for vcg_graph in vcg_graphs:
        all_edges += vcg_graph.edges
    return all_edges


def map_vcg_nodes_to_call_entries(vcg_graphs: list[VCG_Graph]) -> dict[str, FunctionCalleeEntry]:
    fn_callee_map: dict[str, FunctionCalleeEntry] = {}
    for vcg_graph in vcg_graphs:
        for n in vcg_graph.nodes:
            has_function_name = n.label.function_name
            fn_name = n.label.function_name if has_function_name else n.title
            if "." in fn_name:  # removes .constprop.0, .isra, ...
                split_dots = fn_name.split(".")
                fn_name = split_dots[0]
            is_symbol_mapped = fn_name in fn_callee_map
            is_stack_size_defined = is_symbol_mapped and isinstance(
                fn_callee_map[fn_name].node.label.stack_size, int
            )
            if not is_symbol_mapped:
                fn_callee_map[fn_name] = FunctionCalleeEntry(
                    title=fn_name,
                    node=n,
                    worst_stack_use=-1,
                    edges=[],
                    visited=False,
                )
            elif not is_stack_size_defined and isinstance(n.label.stack_size, int):
                fn_callee_map[fn_name].node.label = n.label
            else:
                # TODO add definition or declaration source path?!
                pass

    return fn_callee_map


def map_vcg_call_edges_to_call_entries(
    fn_callee_map: dict[str, FunctionCalleeEntry], edges: list[VCG_Edge]
) -> dict[str, FunctionCalleeEntry]:
    err_unmatched_edges: set[str] = set()
    for e in edges:
        fn_name = e.sourcename
        fn_name_and_path = fn_name.split(":", 1)
        if fn_name not in fn_callee_map and len(fn_name_and_path) == 2:
            fn_name = fn_name_and_path[1]
        if "." in fn_name:  # removes .constprop.0, .isra, ...
            split_dots = fn_name.split(".")
            fn_name = split_dots[0]
        if fn_name in fn_callee_map:
            fn_callee_map[fn_name].edges += [e]
        else:
            err_unmatched_edges.add(fn_name)
            logger.debug(f"err #{len(err_unmatched_edges)} no node matches call edge: {e}")
    return fn_callee_map


def deepest_call_tree(
    f: FunctionCalleeEntry,
    fn_callee_map: dict[str, FunctionCalleeEntry],
    stats: ThreadStats,
    visited=None,
) -> tuple[int, list[FunctionCalleeEntry]]:
    if f.worst_stack_use != NO_WORST_STACK_SIZE_YET:
        return (f.worst_stack_use, [])
    visited = [f] + (visited or [])
    result: tuple[int, list[FunctionCalleeEntry]] = (0, [])

    for call_edge in f.edges:
        if call_edge.targetname == GCC_INDIRECT_CALL_LABEL:
            if f.title in stats.unresolved_calls:
                stats.unresolved_calls[f.title] += 1
            else:
                stats.unresolved_calls[f.title] = 1
        fn_target_name_and_path = call_edge.targetname.split(":", 1)
        callee_name = call_edge.targetname
        if callee_name not in fn_callee_map and len(fn_target_name_and_path) == 2:
            callee_name = fn_target_name_and_path[1]
        if "." in callee_name:  # removes .constprop.0, .isra, ...
            split_dots = callee_name.split(".")
            callee_name = split_dots[0]
        if callee_name not in fn_callee_map:
            continue
        callee_node = fn_callee_map[callee_name]
        if callee_node not in visited:
            candidate = deepest_call_tree(callee_node, fn_callee_map, stats, visited)
            if candidate[0] > result[0]:
                result = candidate

    if not isinstance(f.node.label.stack_size, int):
        stats.missing_stack_sizes += [f.title]
    stack_size = f.node.label.stack_size if isinstance(f.node.label.stack_size, int) else 0
    result = (result[0] + stack_size, [f] + result[1])
    f.worst_stack_use = result[0]
    return result
