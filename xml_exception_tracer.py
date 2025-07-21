import xml.etree.ElementTree as ET
import networkx as nx
import argparse
from pathlib import Path
from pprint import pprint

def parse_workflow_with_groups(xml_file_path):
    tree = ET.parse(xml_file_path)
    root = tree.getroot()

    graph = nx.DiGraph()
    exceptions_info = {}
    condition_to_group = {}

    # Étape 1 : Associer chaque <condition> à son <conditionGroup>
    for group in root.findall(".//conditionGroup"):
        group_id = group.attrib.get("id")
        for condition in group.findall("condition"):
            cond_id = condition.attrib.get("id")
            if cond_id:
                condition_to_group[cond_id] = group_id

    # Étape 2 : Construire le graphe et détecter les exceptions
    for elem in root.iter():
        elem_id = elem.attrib.get("id")
        if elem_id and elem.tag in ["fork", "condition"]:
            graph.add_node(elem_id, type=elem.tag)

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
                        "path": [],
                        "group": condition_to_group.get(elem_id)
                    }

            # Ajouter le jump_to pour la condition
            if elem.tag == "condition":
                jump_elem = elem.find("success/jump")
                if jump_elem is not None:
                    dest = jump_elem.attrib.get("location")
                    if dest:
                        graph.add_edge(elem_id, dest, label="success")
                        if elem_id in exceptions_info:
                            exceptions_info[elem_id]["jump_to"] = dest

    # Étape 3 : Résoudre les chemins menant à chaque exception
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
    parser.add_argument("xml_file", type=str, help="Path to the XML workflow file")
    args = parser.parse_args()

    xml_path = Path(args.xml_file)
    if not xml_path.exists():
        print(f"File not found: {xml_path}")
        return

    result = parse_workflow_with_groups(xml_path)
    pprint(result)

if __name__ == "__main__":
    main()
