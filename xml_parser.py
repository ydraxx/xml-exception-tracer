import os
import xml.etree.ElementTree as ET
from collections import defaultdict

def get_xml_files(xml_path: str):
    """Retrieve XML files from the specified path."""
    return [
        os.path.normpath(os.path.join(root, filename))
        for root, _, filenames in os.walk(xml_path)
        for filename in filenames if filename.endswith('_cfg.xml')
    ]

def parse_workflow_info(xml_file_path: str):
    """Parse workflow info from XML file."""
    try:
        tree = ET.parse(xml_file_path)
        root = tree.getroot()
        wfd = root.find(".//wfd")
        if wfd is None:
            return None, None, None
        return wfd.get("WorkflowName"), wfd.get("WorkflowDiagram"), wfd.get("Initialization")
    except (FileNotFoundError, ET.ParseError, Exception):
        return None, None, None

def show_ini_files(path_to_xml: str):
    """Parse initialization XML to extract event groups and prefilters."""
    try:
        with open(path_to_xml, 'r', encoding='utf-8') as f:
            xml_string = f.read().replace("&", "&amp;")
        root = ET.fromstring(xml_string)
    except FileNotFoundError:
        return {"error": f"Fichier non trouvé : {path_to_xml}"}
    except Exception as e:
        return {"error": str(e)}

    result = {
        "eventGroups": defaultdict(lambda: {"events": []}),
        "preFiltersGroupedByEntities": defaultdict(list)
    }

    # Event list
    event_list_section = root.find(".//eventList")
    if event_list_section is not None:
        has_groups = any(child.tag != "event" for child in event_list_section)
        if has_groups:
            for group in event_list_section:
                for event in group.findall("event"):
                    result["eventGroups"][group.tag]["events"].append(event.attrib)
        else:
            result["eventGroups"]["__root__"]["events"] = [event.attrib for event in event_list_section.findall("event")]

    # Prefilter list
    prefilters_section = root.find(".//preFilterList")
    if prefilters_section is not None:
        for prefilter in prefilters_section.findall('preFilter'):
            entities = prefilter.attrib.get('entities', '')
            condition = prefilter.attrib.get('condition', 'NO_CONDITION')
            result["preFiltersGroupedByEntities"][entities].append(condition)

    return result
