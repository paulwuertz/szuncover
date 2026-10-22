import re

from pydantic import BaseModel
from pydantic.experimental.missing_sentinel import MISSING

GCC_INDIRECT_CALL_LABEL = "__indirect_call"


# TODO add dynamic allocation parsing?
class VCG_Label(BaseModel):
    file_name: str | MISSING = MISSING
    function_name: str | MISSING = MISSING
    line: int | MISSING = MISSING
    column: int | MISSING = MISSING
    stack_size: int | MISSING = MISSING
    stack_qualifier: str | MISSING = MISSING


class VCG_Node(BaseModel):
    title: str
    label: VCG_Label | MISSING = MISSING


class VCG_Edge(BaseModel):
    sourcename: str
    targetname: str
    label: str | MISSING = MISSING


class VCG_Graph(BaseModel):
    title: str
    nodes: list[VCG_Node]
    edges: list[VCG_Edge]


class FunctionCalleeEntry(BaseModel):
    title: str
    node: VCG_Node
    node_declaration: str | MISSING = MISSING
    node_definition: str | MISSING = MISSING
    edges: list[VCG_Edge]
    worst_stack_use: int
    visited: bool


class FunctionCallTree(BaseModel):
    root: FunctionCalleeEntry
    node_declaration: str | MISSING = MISSING
    node_definition: str | MISSING = MISSING
    edges: list[VCG_Edge]


class VCG_Parser:
    su_marker_pattern = r"(\d+)\s+bytes\s+\((.*?)\)"

    @staticmethod
    def parse_vcg_label_attributes(label_str: str):
        vcg_label_lines = label_str.split("\\n")

        function_name = vcg_label_lines[0] if len(vcg_label_lines) >= 1 else None
        fp_split = (
            vcg_label_lines[1].split(":") if len(vcg_label_lines) >= 2 else [None, None, None]
        )
        line = int(fp_split[-2]) if len(fp_split) >= 3 and fp_split[-2] else None
        column = int(fp_split[-1]) if len(fp_split) >= 3 and fp_split[-1] else None
        file_name = ":".join(fp_split[:-2]) if len(fp_split) >= 3 and fp_split[0] else None
        # callgraph with su MARKERS - Match stacksize and qualifier in i.e. '15 bytes (static)'
        stacksize_marker = vcg_label_lines[2] if len(vcg_label_lines) >= 3 else ""
        match = re.search(VCG_Parser.su_marker_pattern, stacksize_marker)
        stack_size = int(match.group(1)) if match else None
        stack_qualifier = match.group(2) if match else None
        if function_name and len(vcg_label_lines) == 1:
            return VCG_Label(
                function_name=function_name,
            )
        if function_name and line and column and file_name and len(vcg_label_lines) == 2:
            return VCG_Label(
                function_name=function_name,
                file_name=file_name,
                line=line,
                column=column,
            )
        elif function_name and line and column and file_name and stack_size and stack_qualifier:
            return VCG_Label(
                function_name=function_name,
                file_name=file_name,
                line=line,
                column=column,
                stack_size=stack_size,
                stack_qualifier=stack_qualifier,
            )
        else:
            # TODO log error/warning?
            return VCG_Label()

    @staticmethod
    def parse_vcg_attributes(attr_str: str):
        attribute_pattern = r'(\w+)\s*:\s*(?:"([^"]*)"|(\S+))'
        attributes = re.findall(attribute_pattern, attr_str)
        parsed_dict = {match[0]: match[1] if match[1] else match[2] for match in attributes}
        return parsed_dict

    @staticmethod
    def parse_node(node_str: str) -> VCG_Node:
        attributes = VCG_Parser.parse_vcg_attributes(node_str)
        title = attributes["title"] if "title" in attributes else ""
        label = attributes["label"] if "label" in attributes else ""
        vcg_label = VCG_Parser.parse_vcg_label_attributes(label)
        if title and label:
            return VCG_Node(title=title, label=vcg_label)
        if title:
            return VCG_Node(title=title)
        else:
            return VCG_Node(title=title)  # TODO error handling/logwarning?

    @staticmethod
    def parse_edge(node_str: str) -> VCG_Edge:
        attributes = VCG_Parser.parse_vcg_attributes(node_str)
        sourcename = attributes["sourcename"] if "sourcename" in attributes else ""
        targetname = attributes["targetname"] if "targetname" in attributes else ""
        label = attributes["label"] if "label" in attributes else ""
        if sourcename and targetname and label:
            return VCG_Edge(sourcename=sourcename, targetname=targetname, label=label)
        if sourcename and targetname:
            return VCG_Edge(sourcename=sourcename, targetname=targetname)
        else:
            # TODO log error/warning or empty ok?
            return VCG_Edge(sourcename=sourcename, targetname=targetname)

    @staticmethod
    def parse_vcg_graph(graph_str: str):
        lines = graph_str.splitlines()
        # looked at gcc/toplev.cc::lang_dependent_init
        # assume exactly one edge / node per line and graph+title in first line
        graph_decl = lines[0] if len(lines) >= 1 else ""
        title = ""
        # strip graph+title and quotes
        if graph_decl.startswith("graph: { title: "):
            title = graph_decl.replace("graph: { title: ", "")
            title = title[1:-1]
        else:
            pass  # TODO error log

        nodes = []
        edges = []
        for line in lines[1:]:
            line = line[:-2] if line.endswith(" }") else line
            if line.startswith("node: { "):
                node_str = line.replace("^node: { ", "")
                n = VCG_Parser.parse_node(node_str)
                nodes += [n]
            elif line.startswith("edge: { "):
                edge_str = line.replace("edge: { ", "")
                e = VCG_Parser.parse_edge(edge_str)
                edges += [e]
            elif line.startswith("}"):
                break

        graph = VCG_Graph(title=title, edges=edges, nodes=nodes)
        return graph
