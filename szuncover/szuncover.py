#!/usr/bin/env python

import argparse
import logging

from calltree import (
    get_vcg_graphs_from_build_dir,
    get_all_edges_from_vcg_graphs,
    map_vcg_nodes_to_call_entries,
    map_vcg_call_edges_to_call_entries,
    ThreadStats,
)
from config import load_config
from report_output import print_stack_size_report

logger = logging.getLogger(__name__)


def parse_args():
    """Parse command line arguments"""
    argparser = argparse.ArgumentParser(allow_abbrev=False)

    argparser.add_argument("--build_dir", help="")
    argparser.add_argument("--config_file", help="")
    argparser.add_argument("--debug", action="store_true", help="Print extra debugging information")

    return argparser.parse_args()


def main():
    """Main function of log parser"""
    args = parse_args()

    if args.debug:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

    conf = load_config(args.config_file)
    if not conf:
        print("Config file exception, exiting...")
        sys.exit(1)

    vcg_graphs = get_vcg_graphs_from_build_dir(args.build_dir)
    edges = get_all_edges_from_vcg_graphs(vcg_graphs)
    call_entries = map_vcg_nodes_to_call_entries(vcg_graphs)
    fn_callee_map = map_vcg_call_edges_to_call_entries(call_entries, edges)

    print_stack_size_report(fn_callee_map, conf)
    print("hi")


if __name__ == "__main__":
    main()
