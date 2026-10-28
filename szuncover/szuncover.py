#!/usr/bin/env python

import argparse
import logging
import sys

from szuncover.calltree import (
    get_all_edges_from_vcg_graphs,
    get_vcg_graphs_from_build_dir,
    map_vcg_call_edges_to_call_entries,
    map_vcg_nodes_to_call_entries,
)
from szuncover.config import load_config
from szuncover.report_output import print_stack_size_report

logger = logging.getLogger()


def parse_args():
    """Parse command line arguments"""
    argparser = argparse.ArgumentParser(
        description="Analyses C/C++ build output for code size, static variables, and stack usage.",
        allow_abbrev=False,
        formatter_class=argparse.RawTextHelpFormatter,
    )

    argparser.add_argument(
        "--build_dir",
        required=True,
        help="Directory where the firmware is build and .ci files containing call and stack size information are searched",
    )
    argparser.add_argument(
        "--config_file",
        required=True,
        help="""Config file containing a list of threads and a list to resolve dynamic function calls.
    Example:
        {
            "threads": [
                { "thread_entry_name": "a", "stack_size": 128 },
                { "thread_entry_name": "b", "stack_size": 256 },
                { "thread_entry_name": "c", "stack_size": 1024 }
            ],
            "dynamic_calls": [
                { "caller": "a", "callees": [ "c" ] },
                { "caller": "b", "callees": [ null ] }
            ]
        }

    * if a functions dynamic callee is set to null it means i.e. a callback is set to a nullpointer so no call will be executed
    * if a a thread or dynamic call entry is not found in the functions a warning will be logged
    """,
    )
    argparser.add_argument("--debug", action="store_true", help="Print extra debugging information")

    return argparser.parse_args()


def main():
    """Main function of log parser"""
    args = parse_args()

    if args.debug:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)
    logging.basicConfig(format="%(message)s")

    conf = load_config(args.config_file)
    if not conf:
        print("Config file exception, exiting...")
        sys.exit(1)

    vcg_graphs = get_vcg_graphs_from_build_dir(args.build_dir)
    edges = get_all_edges_from_vcg_graphs(vcg_graphs)
    call_entries = map_vcg_nodes_to_call_entries(vcg_graphs)
    fn_callee_map = map_vcg_call_edges_to_call_entries(call_entries, edges)

    print_stack_size_report(fn_callee_map, conf)


if __name__ == "__main__":
    main()
