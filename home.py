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
    """Initialize session state variables."""
    if 'exceptions_loaded' not in st.session_state:
        st.session_state.exceptions_loaded = False
    if 'exceptions' not in st.session_state:
        st.session_state.exceptions = []
    if 'llm_results' not in st.session_state:
        st.session_state.llm_results = defaultdict(str)


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
                value = value.strip().replace(";", "")  # Remove semicolon if present
                filter_values[filter_name].add(value)
    return {k: sorted(list(v)) for k, v in filter_values.items()}  # Convert sets to sorted lists


def display_ini_result(result: dict):
    if "error" in result:
        st.error(result["error"])
        return

    # Display event groups
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


    # Display prefilters grouped by entities
    st.subheader("Prefilter per entities")
    if result["preFiltersGroupedByEntities"]:
        for entity, conditions in result["preFiltersGroupedByEntities"].items():
            with st.expander(f"Entitie: `{entity}` ({len(conditions)} conditions)"):

                # Extract filter values
                filter_values = extract_filter_values(conditions)
                filter_names = list(filter_values.keys())
                num_filters = len(filter_names)

                # Condition modifiée ici
                all_single_condition = all(len(condition.split(',')) == 1 for condition in conditions)


                if all_single_condition and num_filters > 0 :
                    # Process and display results (simplified for single condition per filter)
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

                # Display single-select input for each filter
                for i, filter_name in enumerate(filter_names):
                    with cols[i]:
                        filters[filter_name] = st.selectbox(  
                            f"{filter_name}:",
                            options=[""] + filter_values[filter_name], 
                            index=0,  
                        )

                # Process and display results
                results = []
                for condition in conditions:
                    parts = [part.strip() for part in condition.split(',')] 
                    filtered_parts = []

                    # Check if condition matches the selected filters
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

                            # Store the other filters with the possible values
                            for other_filter in other_filters:
                                if other_filter in possible_values:
                                    values_str = ", ".join(possible_values[other_filter])
                                    output += f"{values_str}"
                                else:
                                    output += f" **{other_filter} == All values**"
                        results.append(output)

                # Combine results and display them in a single line
                if results:
                    for other_filter in other_filters:
                        st.markdown(f"- **{other_filter}**: {', '.join(results)}")
    else:
        st.write("No prefilter found.")


def display_exceptions(exceptions, selected_groups):
    """Display exceptions based on selected groups."""
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
    """Display the details for a single exception."""
    
    default_prompt = """You are acting as an AI assistant. Your primary task is to analyze and summarize the function "execute()" or any similar function within the provided code. 
Begin by thoroughly reviewing all the code to understand its context.

Focus on explaining the purpose and functionality of "execute()" and similar functions. 

Offer a concise summary that highlights the key elements of the code, including any relevant actions performed by other functions that help clarify the overall objective of the code. 
Avoid detailed explanations of other functions unless they contribute significant insight into the code's purpose.
Don't put any code in your answer. 
The code could contain two parts, try to understand the functions of the second one to explain the first one. 

Your summary is destinated to non develop people, so don't use technical details. If the code includes a list of values, ensure to mention them in your explanation :"""

    model_names = ["gemini-2.0-flash-001", "claude-sonnet-4", "gpt-4o-mini-2024-07-18"]
    exception_id = exception['condition_id']

    with st.expander(f'**{exception["condition_id"]}**'):
        st.write(f"**Group:** {exception['condition_group']}  \n**Type:** {exception['type']}  \n**Format:** {exception['format']}  \n**Path:** {exception['path']}")

        prompt_custom_key = f"prompt_custom_{exception['condition_group']}/{exception['condition_id']}"
        if prompt_custom_key not in st.session_state:
            st.session_state[prompt_custom_key] = False

        text_area_visible_key = f"text_area_visible_{exception['condition_group']}/{exception['condition_id']}"
        if text_area_visible_key not in st.session_state:
            st.session_state[text_area_visible_key] = False
            
        prompt_value_key = f"prompt_value_{exception['condition_group']}/{exception['condition_id']}"
        if prompt_value_key not in st.session_state:
            st.session_state[prompt_value_key] = default_prompt

        model_name_key = f"model_name_selected_{exception['condition_group']}/{exception['condition_id']}"
        if model_name_key not in st.session_state:
            st.session_state[model_name_key] = model_names[0]

        a, b, c = print_code(exception=exception['condition_id'])
        exception_code, exception_name, code_dep = a, b, c

        if not exception_code:
            disabled = True
        else:
            disabled = False

        show_code_key = f"show_code_{exception['condition_group']}/{exception['condition_id']}"
        if show_code_key not in st.session_state:
            st.session_state[show_code_key] = False

        show_dep_key = f"show_dep_{exception['condition_group']}/{exception['condition_id']}"
        if show_dep_key not in st.session_state:
            st.session_state[show_dep_key] = False


        # CASE WHEN CODE EXCEPTION IS NOT FOUND
        if not a:
            service_folder = exception["condition_id"].split('.')[0]
            service_folder, code_directory = find_directory(service_folder)
            files_folder = os.path.join(xml_cfg['XML_PATH'], "codes", code_directory, service_folder)
            if os.path.exists(files_folder):
                files = [f for f in os.listdir(files_folder)
                       if os.path.isfile(os.path.join(files_folder, f )) and 
                       os.path.join(files_folder, f ).endswith(".cc")]
                files = [''] + files
                replace_exception_name = st.selectbox(label="No exception code found. Select the right code.", 
                                                  options=files, 
                                                  key=f"disabled_{exception['condition_group']}/{exception['condition_id']}_selectbox")
                if replace_exception_name != '':
                    exception_id = exception['condition_id'].split('.')[0] + '.' + replace_exception_name.split('_')[1].split('.')[0]
                    exception_code, exception_name, code_dep = replace_print_code(exception=exception_id)
            if not exception_code:
                disabled = True
            else:
                disabled = False


        col1, col2, col3, col4 = st.columns(4) 

        # BUTTON CUSTOM PROMPT
        with col1:
            if st.button(label='Custom prompt', key=f"prompt_{exception['condition_group']}/{exception['condition_id']}_button",
                         use_container_width=True, disabled=disabled):
                st.session_state[prompt_custom_key] = not st.session_state[prompt_custom_key]

        # BUTTON SHOW CODE
        with col2: 
            if st.button(label='Show exception code', key=f"dep_{exception['condition_group']}/{exception['condition_id']}_button",
                         use_container_width=True, disabled=disabled):
                st.session_state[show_code_key] = not st.session_state[show_code_key]

        # BUTTON SHOW DEPENDENCIES
        with col3:
            if st.button(label='Show includes code', key=f"codes_{exception['condition_group']}/{exception['condition_id']}_button",
                         use_container_width=True, disabled=disabled):
                st.session_state[show_dep_key] = not st.session_state[show_dep_key]

        # BUTTON AI
        with col4:
            if st.button(label='Ask AI', key=f"AI_{exception['condition_group']}/{exception['condition_id']}_button", 
                         use_container_width=True, disabled=disabled):
                result = llm_request(exception=exception_id, 
                                     prompt_struct=st.session_state[prompt_value_key],
                                     model_name=st.session_state[model_name_key])
                st.session_state.llm_results[exception['condition_id']] = result 

        # RESULT CUSTOM PROMPT
        if st.session_state[prompt_custom_key]:
            prompt_struct_key = f"input_{exception['condition_group']}/{exception['condition_id']}"
            
            if st.button(label="Change prompt", key=f"change_prompt_{exception['condition_group']}/{exception['condition_id']}_button"):
                st.session_state[text_area_visible_key] = not st.session_state[text_area_visible_key]
            
            st.session_state[model_name_key] = st.selectbox(
                label="Model:", 
                options=model_names, 
                key=f"model_name_{exception['condition_group']}/{exception['condition_id']}"
            )

            if st.session_state[text_area_visible_key]:
                st.session_state[prompt_value_key] = st.text_area(label="Prompt:", value=st.session_state[prompt_value_key], key=prompt_struct_key)
            else:
                st.code(f"{st.session_state[prompt_value_key]}  \n\nPart 1:  \nFile: {exception_name}  \nCode:  \n{exception_code}  \n\nPart 2:  \nCode:  \n{code_dep}", 
                        language='markdown')

        # RESULT SHOW CODE
        if st.session_state[show_code_key]:
            st.code(f"File: {exception_name}  \nCode:  \n{exception_code}", language='cpp')

        # RESULT SHOW DEP
        if st.session_state[show_dep_key]:
            st.code(code_dep, language='cpp')

        # IA RESULT
        if exception['condition_id'] in st.session_state.llm_results:
            st.write(st.session_state.llm_results[exception['condition_id']])


def main():
    st.set_page_config(layout="wide", 
                       page_title='AIDoc', 
						page_icon=app_cfg['LOGO_PATH']
                       )
    
    st.logo(image=app_cfg['LOGO_PATH'])

    st.markdown(
        """
        <style>
        [data-testid="stExpander"] {
            background-color: #F5F7FF;
        }
        img[data-testid="stLogo"] {
            height: 7.5rem;
        }
        [data-testid="stDecoration"] {background: #0059ff;}
        </style>
        """,
        unsafe_allow_html=True
    )

    col1, col2, col3, col4, col5, col6, col7, col8 = st.columns([1, 1, 1, 1, 1, 1, 1, 1])
    with col8:
        st.button('Update code', key='button2', use_container_width=True, on_click=update_bitbucket)
    
    st.title('STP Workflow Tracer')

    initialize_session_state()
    
    files = get_xml_files(xml_cfg['XML_PATH'])
    file_map = {os.path.basename(file).split('_cfg')[0]: file for file in files}

    selected_file_name = st.selectbox("Workflow",  list(file_map.keys()))
    xml_selected = file_map[selected_file_name]

    workflow_name, workflow_diagram, initialization = get_workflow_info(xml_file_path=xml_selected)
    initialization_path = os.path.join(xml_cfg['XML_PATH'], initialization)
    wfd_path = os.path.join(xml_cfg['XML_PATH'], workflow_diagram)

    result = show_ini_files(initialization_path)
    
    # Initialization file
    with st.expander('Entities and conditions', expanded=False):
        display_ini_result(result)

    if st.button('Get exceptions', key='button1'):
        graph = build_workflow_graph(xml_file=wfd_path)
        st.session_state.exceptions = extract_exceptions(graph=graph, xml_file=wfd_path)
        st.session_state.exceptions_loaded = True
        all_groups = set(exception.get('condition_group', 'Autre') for exception in st.session_state.exceptions)
        st.session_state.selected_groups = list(all_groups)

    # Side bar
    with st.sidebar:
        if st.session_state.exceptions_loaded:
            st.header("Exception group")
            exceptions = st.session_state.exceptions
            if exceptions:
                all_groups = sorted(list(set(exception.get('condition_group', 'Autre') for exception in exceptions)))
                
                # Create checkboxes for each exception group
                for group in all_groups:
                    group_display = "No exception group" if group == 'None' else group
                    is_selected = st.checkbox(group_display, value=(group in st.session_state.selected_groups))
                    
                    if is_selected and group not in st.session_state.selected_groups:
                        st.session_state.selected_groups.append(group)
                    elif not is_selected and group in st.session_state.selected_groups:
                        st.session_state.selected_groups.remove(group)

    # WorkFlow Diagram
    if st.session_state.exceptions_loaded:
        exceptions = st.session_state.exceptions
        if exceptions:
            display_exceptions(exceptions, st.session_state.selected_groups)
        else:
            st.write("0 exception found.")


if __name__ == "__main__":
    main()
