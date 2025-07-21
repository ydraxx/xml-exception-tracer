import xml.etree.ElementTree as ET
import networkx as nx
import argparse
from pathlib import Path
from pprint import pprint

def parse_workflow(xml_file_path):
    tree = ET.parse(xml_file_path)
    root = tree.getroot()

    graph = nx.DiGraph()
    exceptions_info = {}
    nodes_by_id = {}

    for elem in root:
        elem_id = elem.attrib.get("id")
        if elem_id and elem.tag in ["fork", "condition"]:
            nodes_by_id[elem_id] = elem
            graph.add_node(elem_id, type=elem.tag)

            # Success / Failure paths
            for outcome in elem:
                if outcome.tag in ["success", "failure"]:
                    for jump in outcome.findall("jump"):
                        dest = jump.attrib.get("location")
                        if dest:
                            graph.add_edge(elem_id, dest, label=outcome.tag)

                elif outcome.tag == "exception":
                    graph.nodes[elem_id]["exception"] = outcome.attrib
                    exceptions_info[elem_id] = {
                        "exception": outcome.attrib,
                        "jump_to": None,
                        "path": []
                    }

            # Jump après exception
            jump_elem = elem.find("success/jump")
            if jump_elem is not None and elem.tag == "condition":
                dest = jump_elem.attrib.get("location")
                if dest:
                    graph.add_edge(elem_id, dest, label="success")
                    if elem_id in exceptions_info:
                        exceptions_info[elem_id]["jump_to"] = dest

    # Résolution des chemins vers les conditions avec exception
    for target in exceptions_info:
        for source in graph.nodes:
            if source == target:
                continue
            try:
                path = nx.shortest_path(graph, source=source, target=target)
                exceptions_info[target]["path"].append(path)
            except nx.NetworkXNoPath:
                continue

    return exceptions_info

def main():
    parser = argparse.ArgumentParser(description="Extract exception info from XML workflow")
    parser.add_argument("xml_file", type=str, help="Path to the XML file")
    args = parser.parse_args()

    xml_path = Path(args.xml_file)
    if not xml_path.exists():
        print(f"Error: File '{xml_path}' does not exist.")
        return

    result = parse_workflow(xml_path)
    pprint(result)

if __name__ == "__main__":
    main()
