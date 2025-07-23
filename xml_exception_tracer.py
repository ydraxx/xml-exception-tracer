import xml.etree.ElementTree as ET
import networkx as nx

def build_workflow_graph(xml_file):

    try:
        tree = ET.parse(xml_file)
        root = tree.getroot()
    except ET.ParseError as e:
        print(f"Erreur lors de l'analyse du XML : {e}")
        return None

    graph = nx.DiGraph() 

    start_node = root.find(".//start")
    if start_node is None:
        print("Élément <start> introuvable.")
        return None

    start_id = start_node.get("id")
    graph.add_node(start_id, type="start")

    def explore_element(element, source_node_id, edge_label=None):
        for child in element:
            if child.tag == "fork":
                fork_id = child.get("id")
                graph.add_node(fork_id, type="fork")
                graph.add_edge(source_node_id, fork_id, label=edge_label if edge_label else "")

                explore_fork_branches(child, fork_id)

            elif child.tag == "condition":
                condition_id = child.get("id")
                graph.add_node(condition_id, type="condition")
                graph.add_edge(source_node_id, condition_id, label=edge_label if edge_label else "")

                explore_condition_branches(child, condition_id)

            elif child.tag == "operation":
                operation_id = child.get("id")
                graph.add_node(operation_id, type="operation")
                graph.add_edge(source_node_id, operation_id, label=edge_label if edge_label else "")

                explore_element(child, operation_id)

            elif child.tag == "jump":
                target_location = child.get("location")
                graph.add_node(target_location, type="jump")
                graph.add_edge(source_node_id, target_location, label=edge_label if edge_label else "")

            elif child.tag == "end":
                end_id = child.get("id")
                graph.add_node(end_id, type="end")
                graph.add_edge(source_node_id, end_id, label=edge_label if edge_label else "")

            elif child.tag == "conditionGroup":
                condition_group_id = child.get("id")
                graph.add_node(condition_group_id, type="conditionGroup")
                graph.add_edge(source_node_id, condition_group_id, label=edge_label if edge_label else "")
                explore_condition_group_branches(child, condition_group_id)

            elif child.tag == "label":
                label_id = child.get("id")
                graph.add_node(label_id, type="label")
                graph.add_edge(source_node_id, label_id, label=edge_label if edge_label else "")
                explore_element(child, label_id)


    def explore_fork_branches(fork_element, fork_id):
        success_branch = fork_element.find("success")
        failure_branch = fork_element.find("failure")

        if success_branch is not None:
            explore_element(success_branch, fork_id, edge_label="Success")
        if failure_branch is not None:
            explore_element(failure_branch, fork_id, edge_label="Failure")

    def explore_condition_branches(condition_element, condition_id):
        success_branch = condition_element.find("success")
        if success_branch is not None:
            explore_element(success_branch, condition_id, edge_label="Success")

    def explore_condition_group_branches(condition_group_element, condition_group_id):
        for child in condition_group_element:
            if child.tag == "condition":
                condition_id = child.get("id")
                graph.add_node(condition_id, type="condition")
                graph.add_edge(condition_group_id, condition_id)

    explore_element(start_node, start_id)

    return graph


def extract_exceptions_and_paths_from_graph(graph, xml_file):

    try:
        tree = ET.parse(xml_file)
        root = tree.getroot()
    except ET.ParseError as e:
        print(f"Erreur lors de l'analyse du XML : {e}")
        return []

    exceptions_data = []

    def find_path_with_labels(graph, start, end):
        def get_path_with_labels(current, target, visited, path):
            visited.add(current)
    
            if current == target:
                return True
    
            for neighbor in graph.successors(current):
                edge_label = graph.get_edge_data(current, neighbor).get("label", "")
                if neighbor not in visited:
                    path.append((current, edge_label, neighbor))
                    if get_path_with_labels(neighbor, target, visited, path):
                        return True
                    path.pop()
    
            visited.remove(current)
            return False
    
        visited = set()
        path = []
        found = get_path_with_labels(start, end, visited, path)
    
        if not found:
            return None
    
        # Formate le chemin en ajoutant les labels
        formatted = []
        for src, label, dst in path:
            formatted.append(f"{src} --[{label}]--> {dst}")
        return " -> ".join(formatted)


    for condition in root.findall(".//condition"):
        exception_element = condition.find("exception")
        if exception_element is not None:
            condition_id = condition.get("id")
            start_node_id = root.find(".//start").get("id")
            path = find_path_with_labels(graph, start_node_id, condition_id)

            exception_info = {
                "condition_id": condition_id,
                "condition_group": condition.get("conditionG", "None"),
                "type": exception_element.get("type"),
                "format": exception_element.get("format"),
                "text": exception_element.get("text", "None"),
                "path": path,
            }
            exceptions_data.append(exception_info)

    return exceptions_data


def main():
    xml_file = "C:/Users/madecco/Projects/egf-ml/app-xml-exception-tracer/ValidPayDocServer_wfd.xml"
    graph = build_workflow_graph(xml_file)

    if graph is None:
        print("Erreur lors de la construction du graphe.")
        return

    exceptions = extract_exceptions_and_paths_from_graph(graph, xml_file)

    if exceptions:
        print("\nExceptions trouvées :")
        for exception in exceptions:
            print("--------------------------------------")
            print(f"Condition ID: {exception['condition_id']}")
            print(f"Condition Group: {exception['condition_group']}")
            print(f"Type: {exception['type']}")
            print(f"Format: {exception['format']}")
            print(f"Text: {exception['text']}")
            print(f"Workflow Path: {exception['path']}")
    else:
        print("Aucune exception trouvée.")

    print("--------------------------------------")
    print('Exceptions: ' + str(len(exceptions)))


if __name__ == "__main__":
    main()
