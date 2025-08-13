import os
import streamlit as st
import streamlit_nested_layout
from collections import defaultdict

from config import xml_cfg, app_cfg
from graph_xml import build_workflow_graph, extract_exceptions
from llm_request import main as llm_request, print_code, replace_print_code, find_directory
from sessionstate_manager import SessionStateManager
from update_bitbucket import main as update_bitbucket

from utils import init_session_var
from xml_parser import get_xml_files, parse_workflow_info, show_ini_files
from ui_components import display_ini_result, display_exceptions


@st.cache_data
def get_xml_files_cached(xml_path):
    return get_xml_files(xml_path)


@st.cache_data
def show_ini_files_cached(path_to_xml):
    return show_ini_files(path_to_xml)


def initialize_session_state():
    """Initialize required session state variables."""
    init_session_var('exceptions_loaded', False)
    init_session_var('exceptions', [])
    init_session_var('llm_results', defaultdict(str))
    init_session_var('selected_groups', [])


def main():
    st.set_page_config(layout="wide", page_title='AIDoc', page_icon=app_cfg['LOGO_PATH'])
    st.logo(image=app_cfg['LOGO_PATH'])

    st.markdown(
        """
        <style>
        [data-testid="stExpander"] { background-color: #F5F7FF; }
        img[data-testid="stLogo"] { height: 7.5rem; }
        [data-testid="stDecoration"] { background: #0059ff; }
        </style>
        """,
        unsafe_allow_html=True
    )

    # Toolbar buttons
    col1, col2, col3, col4, col5, col6, col7, col8 = st.columns(8)
    with col8:
        st.button('Update code', key='button2', use_container_width=True, on_click=update_bitbucket)

    st.title('STP Workflow Tracer')

    # Init state
    initialize_session_state()

    # Load XML files
    files = get_xml_files_cached(xml_cfg['XML_PATH'])
    file_map = {os.path.basename(file).split('_cfg')[0]: file for file in files}

    # Select workflow
    selected_file_name = st.selectbox("Workflow", list(file_map.keys()))
    xml_selected = file_map[selected_file_name]

    # Get workflow info
    workflow_name, workflow_diagram, initialization = parse_workflow_info(xml_selected)
    initialization_path = os.path.join(xml_cfg['XML_PATH'], initialization)
    wfd_path = os.path.join(xml_cfg['XML_PATH'], workflow_diagram)

    # Entities and conditions
    result = show_ini_files_cached(initialization_path)
    with st.expander('Entities and conditions', expanded=False):
        display_ini_result(result)

    # Get exceptions
    if st.button('Get exceptions', key='button1'):
        graph = build_workflow_graph(xml_file=wfd_path)
        st.session_state.exceptions = extract_exceptions(graph=graph, xml_file=wfd_path)
        st.session_state.exceptions_loaded = True
        st.session_state.selected_groups = list({e.get('condition_group', 'Autre') for e in st.session_state.exceptions})

    # Sidebar: Exception group filter
    with st.sidebar:
        if st.session_state.exceptions_loaded:
            st.header("Exception group")
            exceptions = st.session_state.exceptions
            if exceptions:
                all_groups = sorted(list({e.get('condition_group', 'Autre') for e in exceptions}))
                for group in all_groups:
                    group_display = "No exception group" if group == 'None' else group
                    is_selected = st.checkbox(group_display, value=(group in st.session_state.selected_groups))
                    if is_selected and group not in st.session_state.selected_groups:
                        st.session_state.selected_groups.append(group)
                    elif not is_selected and group in st.session_state.selected_groups:
                        st.session_state.selected_groups.remove(group)

    # Display exceptions
    if st.session_state.exceptions_loaded:
        exceptions = st.session_state.exceptions
        if exceptions:
            display_exceptions(exceptions, st.session_state.selected_groups, llm_request, print_code, replace_print_code, find_directory)
        else:
            st.write("0 exception found.")


if __name__ == "__main__":
    main()
