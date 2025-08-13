from collections import defaultdict
import os
import pandas as pd
import streamlit as st
import streamlit_nested_layout 
import xml.etree.ElementTree as ET

from config import xml_cfg, app_cfg
from graph_xml import build_workflow_graph, extract_exceptions
from llm_request import main as llm_request, print_code, replace_print_code, find_directory
from sessionstate_manager import SessionStateManager
from update_bitbucket import main as update_bitbucket


def initialize_session_state():
    """Initialize session state variables using SessionStateManager."""
    state = SessionStateManager()
    state.init_bulk({
        "exceptions_loaded": False,
        "exceptions": [],
        "llm_results": defaultdict(str),
        "selected_groups": []
    })
    return state


def get_xml_files(xml_path: str):
    """Retrieve XML files from the specified path."""
    files = []
    for root, dirs, filenames in os.walk(xml_path):
        for filename in filenames:
            if filename.endswith('_cfg.xml'):
                files.append(os.path.normpath(os.path.join(root, filename)))
    return files


def get_workflow_info(xml_file_path: str):
    try:
        tree = ET.parse(xml_file_path)
        root = tree.getroot()

        wfd_element = root.find(".//wfd")

        if wfd_element is not None:
            workflow_name = wfd_element.get("WorkflowName")
            workflow_diagram = wfd_element.get("WorkflowDiagram")
            initialization = wfd_element.get("Initialization")
            return workflow_name, workflow_diagram, initialization
        else:
            print(f"Error: The 'wfd' element was not found in the file {xml_file_path}")
            return None, None, None

    except FileNotFoundError:
        print(f"Error: The XML file {xml_file_path} was not found.")
        return None, None, None
    except ET.ParseError as e:
        print(f"Error parsing the XML file {xml_file_path}: {e}")
        return None, None, None
    except Exception as e:
        print(f"An unexpected error occurred while processing the file {xml_file_path}: {e}")
        return None, None, None
    

def show_ini_files(path_to_xml: str):
    try:
        with open(path_to_xml, 'r', encoding='utf-8') as f:
            xml_string = f.read()
    except FileNotFoundError:
        return {"error": f"Fichier non trouvé : {path_to_xml}"}
    except Exception as e:
        return {"error": f"Erreur lors de la lecture du fichier : {e}"}

    try:
        xml_string = xml_string.replace("&", "&amp;")
        root = ET.fromstring(xml_string)
    except ET.ParseError as e:
        return {"error": f"Erreur de parsing XML : {e}"}

    result = {
        "eventGroups": defaultdict(lambda: {"events": []}),
        "preFiltersGroupedByEntities": defaultdict(list)
    }

    # -------- EVENT LIST --------
    event_list_section = root.find(".//eventList")
    if event_list_section is not None:
        has_groups = any(child.tag != "event" for child in event_list_section)

        if has_groups:
            for group in event_list_section:
                group_name = group.tag
                for event in group.findall("event"):
                    event_info = {k: v for k, v in event.attrib.items()}
                    result["eventGroups"][group_name]["events"].append(event_info)
        else:
            result["eventGroups"]["__root__"]["events"] = [{k: v for k, v in event.attrib.items()} for event in event_list_section.findall("event")]

    # -------- PREFILTER LIST --------
    prefilters_section = root.find(".//preFilterList")

    if prefilters_section is not None:
        for prefilter in prefilters_section.findall('preFilter'):
            entities = prefilter.attrib.get('entities', '')
            condition = prefilter.attrib.get('condition', 'NO_CONDITION')
            result["preFiltersGroupedByEntities"][entities].append(condition)

    return result


def extract_filter_values(conditions):
    """Extracts all possible filter values from the conditions."""
    filter_values = defaultdict(set)
    for condition in conditions:
        parts = condition.split(',')
        for part in parts:
            if "==" in part:
                filter_name, value = part.split("==")
                filter_name = filter_name.strip()
                value = value.strip().replace(";", "")
                filter_values[filter_name].add(value)
    return {k: sorted(list(v)) for k, v in filter_values.items()}


def display_ini_result(result: dict):
    if "error" in result:
        st.error(result["error"])
        return

    st.subheader("Event List")
    if result["eventGroups"]:
        for group_name, group_data in result["eventGroups"].items():
            events = group_data["events"]
            display_name = f"Event group: `{group_name}`" if group_name != "__root__" else "No group"
            st.markdown(f"#### {display_name}")

            if events:
                for event in events:
                    event_str = ", ".join([f"{k}: `{v}`" for k, v in event.items()])
                    st.markdown(f"- {event_str}")
            else:
                st.write("No event found in this group.")
    else:
        st.write("No event found.")

    st.subheader("Prefilter per entities")
    if result["preFiltersGroupedByEntities"]:
        for entity, conditions in result["preFiltersGroupedByEntities"].items():
            with st.expander(f"Entitie: `{entity}` ({len(conditions)} conditions)"):

                filter_values = extract_filter_values(conditions)
                filter_names = list(filter_values.keys())
                num_filters = len(filter_names)

                all_single_condition = all(len(condition.split(',')) == 1 for condition in conditions)

                if all_single_condition and num_filters > 0:
                    results_dict = {}
                    for condition in conditions:
                        parts = [part.strip() for part in condition.split(',')]
                        for part in parts:
                            if "==" in part:
                                filter_name, value = part.split("==")
                                filter_name = filter_name.strip()
                                value = value.strip().replace(";", "")
                                if filter_name not in results_dict:
                                    results_dict[filter_name] = []
                                results_dict[filter_name].append(value)

                    for filter_name, values in results_dict.items():
                        st.markdown(f"- **{filter_name}**: {', '.join(values)}")
                    continue 

                cols = st.columns(num_filters)
                filters = {}
                for i, filter_name in enumerate(filter_names):
                    with cols[i]:
                        filters[filter_name] = st.selectbox(
                            f"{filter_name}:",
                            options=[""] + filter_values[filter_name],
                            index=0
                        )

                results = []
                for condition in conditions:
                    parts = [part.strip() for part in condition.split(',')]
                    filtered_parts = []
                    for part in parts:
                        if "==" in part:
                            filter_name, value = part.split("==")
                            filter_name = filter_name.strip()
                            value = value.strip().replace(";", "")

                            if filter_name in filters and filters[filter_name] == value:
                                filtered_parts.append((filter_name, value))

                    if len(filtered_parts) > 0:
                        output = ""
                        for filter_name, selected_value in filtered_parts:
                            other_filters = [f for f in filter_names if f != filter_name]

                            possible_values = defaultdict(list)
                            for part in parts:
                                if all(other_filter in part for other_filter in other_filters) and "==" in part:
                                    other_filter_name, other_filter_value = part.split("==")
                                    other_filter_name = other_filter_name.strip()
                                    other_filter_value = other_filter_value.strip().replace(";", "")
                                    possible_values[other_filter_name].append(other_filter_value)

                            for other_filter in other_filters:
                                if other_filter in possible_values:
                                    values_str = ", ".join(possible_values[other_filter])
                                    output += f"{values_str}"
                                else:
                                    output += f" **{other_filter} == All values**"
                        results.append(output)

                if results:
                    for other_filter in other_filters:
                        st.markdown(f"- **{other_filter}**: {', '.join(results)}")
    else:
        st.write("No prefilter found.")


def display_exceptions(exceptions, selected_groups):
    grouped_exceptions = defaultdict(list)
    for exception in exceptions:
        condition_group = exception.get('condition_group', 'Autre')
        grouped_exceptions[condition_group].append(exception)
    
    for condition_group in list(grouped_exceptions.keys()):
        if condition_group not in selected_groups:
            del grouped_exceptions[condition_group]

    for condition_group, group_exceptions in grouped_exceptions.items():
        condition_group_display = "No exception group" if condition_group == 'None' else condition_group
        st.subheader(condition_group_display)
        for exception in group_exceptions:
            display_exception_details(exception)


def display_exception_details(exception):
    state = SessionStateManager(namespace=f"{exception['condition_group']}/{exception['condition_id']}")
    
    default_prompt = """You are acting as an AI assistant..."""  # Raccourci ici pour lisibilité
    model_names = ["gemini-2.0-flash-001", "claude-sonnet-4", "gpt-4o-mini-2024-07-18"]
    exception_id = exception['condition_id']

    state.init("prompt_custom", False)
    state.init("text_area_visible", False)
    state.init("prompt_value", default_prompt)
    state.init("model_name_selected", model_names[0])
    state.init("show_code", False)
    state.init("show_dep", False)

    a, b, c = print_code(exception=exception['condition_id'])
    exception_code, exception_name, code_dep = a, b, c
    disabled = not bool(exception_code)

    with st.expander(f'**{exception["condition_id"]}**'):
        st.write(f"**Group:** {exception['condition_group']}  \n**Type:** {exception['type']}  \n**Format:** {exception['format']}  \n**Path:** {exception['path']}")

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            if st.button("Custom prompt", disabled=disabled):
                state.toggle("prompt_custom")

        with col2:
            if st.button("Show exception code", disabled=disabled):
                state.toggle("show_code")

        with col3:
            if st.button("Show includes code", disabled=disabled):
                state.toggle("show_dep")

        with col4:
            if st.button("Ask AI", disabled=disabled):
                result = llm_request(
                    exception=exception_id,
                    prompt_struct=state.get("prompt_value"),
                    model_name=state.get("model_name_selected")
                )
                SessionStateManager().get("llm_results")[exception['condition_id']] = result

        if state.get("prompt_custom"):
            if st.button("Change prompt"):
                state.toggle("text_area_visible")

            state.set("model_name_selected", st.selectbox("Model:", model_names))
            
            if state.get("text_area_visible"):
                state.set("prompt_value", st.text_area("Prompt:", value=state.get("prompt_value")))
            else:
                st.code(f"{state.get('prompt_value')}  \n\nPart 1:  \nFile: {exception_name}  \nCode:  \n{exception_code}  \n\nPart 2:  \nCode:  \n{code_dep}", language='markdown')

        if state.get("show_code"):
            st.code(f"File: {exception_name}  \nCode:  \n{exception_code}", language='cpp')

        if state.get("show_dep"):
            st.code(code_dep, language='cpp')

        if exception['condition_id'] in SessionStateManager().get("llm_results"):
            st.write(SessionStateManager().get("llm_results")[exception['condition_id']])


def main():
    st.set_page_config(layout="wide", page_title='AIDoc', page_icon=app_cfg['LOGO_PATH'])
    st.logo(image=app_cfg['LOGO_PATH'])

    st.markdown("""
        <style>
        [data-testid="stExpander"] { background-color: #F5F7FF; }
        img[data-testid="stLogo"] { height: 7.5rem; }
        [data-testid="stDecoration"] { background: #0059ff; }
        </style>
    """, unsafe_allow_html=True)

    col1, col2, col3, col4, col5, col6, col7, col8 = st.columns([1, 1, 1, 1, 1, 1, 1, 1])
    with col8:
        st.button('Update code', key='button2', use_container_width=True, on_click=update_bitbucket)

    st.title('STP Workflow Tracer')

    state = initialize_session_state()

    files = get_xml_files(xml_cfg['XML_PATH'])
    file_map = {os.path.basename(file).split('_cfg')[0]: file for file in files}
    selected_file_name = st.selectbox("Workflow", list(file_map.keys()))
    xml_selected = file_map[selected_file_name]

    workflow_name, workflow_diagram, initialization = get_workflow_info(xml_file_path=xml_selected)
    initialization_path = os.path.join(xml_cfg['XML_PATH'], initialization)
    wfd_path = os.path.join(xml_cfg['XML_PATH'], workflow_diagram)

    result = show_ini_files(initialization_path)
    with st.expander('Entities and conditions', expanded=False):
        display_ini_result(result)

    if st.button('Get exceptions', key='button1'):
        graph = build_workflow_graph(xml_file=wfd_path)
        state.set("exceptions", extract_exceptions(graph=graph, xml_file=wfd_path))
        state.set("exceptions_loaded", True)
        all_groups = set(exc.get('condition_group', 'Autre') for exc in state.get("exceptions"))
        state.set("selected_groups", list(all_groups))

    with st.sidebar:
        if state.get("exceptions_loaded"):
            st.header("Exception group")
            exceptions = state.get("exceptions")
            if exceptions:
                all_groups = sorted(set(exc.get('condition_group', 'Autre') for exc in exceptions))
                for group in all_groups:
                    group_display = "No exception group" if group == 'None' else group
                    is_selected = st.checkbox(group_display, value=(group in state.get("selected_groups")))
                    if is_selected and group not in state.get("selected_groups"):
                        state.get("selected_groups").append(group)
                    elif not is_selected and group in state.get("selected_groups"):
                        state.get("selected_groups").remove(group)

    if state.get("exceptions_loaded"):
        exceptions = state.get("exceptions")
        if exceptions:
            display_exceptions(exceptions, state.get("selected_groups"))
        else:
            st.write("0 exception found.")


if __name__ == "__main__":
    main()
