from collections import defaultdict
import json
import os
import streamlit as st
import streamlit_nested_layout 

from config import xml_cfg, app_cfg
from comps_exceptions import display_exceptions
from comps_init_stp import show_ini_files, display_ini_result
from func_graph_xml import build_workflow_graph, extract_exceptions
from func_manage_json import JsonManager
from func_manage_xml import get_xml_files, get_workflow_info
from func_update_bitbucket import main as update_bitbucket, get_stp_list
from func_utils import is_admin


st.set_page_config(layout="wide", 
                       page_title='AIDoc', 
						page_icon=app_cfg['LOGO_PATH']
                       )


def initialize_session_state():
    """Initialize session state variables."""
    if 'exceptions_loaded' not in st.session_state:
        st.session_state.exceptions_loaded = False
    if 'exceptions' not in st.session_state:
        st.session_state.exceptions = []
    if 'llm_results' not in st.session_state:
        st.session_state.llm_results = defaultdict(str)
    

def main():
    
    style()

    isadmin, username = is_admin()

    if "page" not in st.session_state:
        st.session_state.page = "Home"

    if st.session_state.page == "Settings":
        col1, col2, col3, col4, col5, col8 = st.columns([1, 1, 1, 1, 1, 1])
        with col1:
            if st.button(label='Home', key='buttonHome', use_container_width=False):
                st.session_state.page = "Home"
                st.rerun()
        st.title('Settings')

        st.subheader('Default prompt')
        with open(app_cfg["JSON_PROMPT"], 'r') as f:
                json_prompt = json.load(f)
        default_prompt = json_prompt["prompt_default"]
        prompt_area = st.text_area(label='Change', 
                             key='default_prompt_text_area',
                             value=default_prompt)
        if st.button(label='Save', key='buttonSavePrompt'):
            json_prompt["prompt_default"] = prompt_area
    
            with open(app_cfg["JSON_PROMPT"], 'w') as f:
                json.dump(json_prompt, f, indent=4)
            st.success("Changes saved successfully!")

        st.subheader('STP to download')
        list_stp = get_stp_list()

        stp_already_selected = JsonManager.get_stp_list()
        selected_stp = []

        for stp in list_stp:
            checked_value = stp in stp_already_selected
            is_checked = st.checkbox(stp, key=f"checkbow_{stp}", value=checked_value)
            if is_checked:
                selected_stp.append(stp)
        
        if st.button(label='Save', key="buttonSaveSTP"):
            JsonManager.change_stp_list(stp_list=selected_stp)
            st.success("Changes saved successfully!")

        with st.sidebar:
                c1, c2, c3 = st.columns([2, 10, 1])
                with c2:
                    st.image(app_cfg["LOGO_PATH"], width=100)
                
                st.write(f"**Welcome {username}!**")


    if st.session_state.page == "Home":
        col1, col2, col3, col4, col5, col8 = st.columns([1, 1, 1, 1, 1, 1])
        with col1:
            if st.button(label='Settings', key='buttonSettings', use_container_width=False, disabled=not isadmin):
                st.session_state.page = "Settings"
                st.rerun()
        with col8:
            st.selectbox(label='Source', options=['Production', 'UAT'], label_visibility="hidden")

        colu1, colu2, colu3, colu4, colu5, colu8 = st.columns([1, 1, 1, 1, 1, 1])
        with colu8:
            st.button(label='Update code', key='button2', use_container_width=True, on_click=update_bitbucket)
        
        st.title('STP Workflow Tracer')

        initialize_session_state()
        
        files = get_xml_files(xml_cfg['XML_PATH'])
        if files == []:
            files = ['No STP uploaded.']
            st.selectbox("Workflow",  files, key="selectBoxNone")
        else:
            file_map = {os.path.basename(file).split('_cfg')[0]: file for file in files}

            selected_file_name = st.selectbox("Workflow",  list(file_map.keys()))
            xml_selected = file_map[selected_file_name]

            workflow_name, workflow_diagram, initialization = get_workflow_info(xml_file_path=xml_selected)
            initialization_path = os.path.join(xml_cfg['XML_PATH'], initialization)
            wfd_path = os.path.join(xml_cfg['XML_PATH'], workflow_diagram)

            result = show_ini_files(initialization_path)

            manage_json = JsonManager()

            # Initialization file
            with st.expander('Entities and conditions', expanded=False):
                display_ini_result(result)

            if st.button('Get exceptions', key='button1'):
                graph = build_workflow_graph(xml_file=wfd_path)
                st.session_state.exceptions = extract_exceptions(graph=graph, xml_file=wfd_path)
                st.session_state.exceptions_loaded = True
                all_groups = set(exception.get('condition_group', 'Autre') for exception in st.session_state.exceptions)
                st.session_state.selected_groups = list(all_groups)
                manage_json.add_exceptions(module_name=workflow_name, 
                                    exceptions_data=st.session_state.exceptions)

            # Side bar
            with st.sidebar:
                c1, c2, c3 = st.columns([2, 10, 1])
                with c2:
                    st.image(app_cfg["LOGO_PATH"], width=100)
                
                st.write(f"**Welcome {username}!**")

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


def style():
    st.markdown(
        """
        <style>
        [data-testid="stExpander"] {
            background-color: #F5F7FF;
            color: black; /* Couleur du texte par défaut */
            border: 1px solid transparent; /* Bordure transparente par défaut */
            border-radius: 0.700rem; /* Coins arrondis par défaut */
            transition: all 0.1s ease; /* Transition pour un effet plus doux */
        }

        [data-testid="stExpander"]:hover {
            border: 1px solid #0059ff; /* Bordure bleue au survol */
            color: #0059ff; /* Texte bleu au survol */
        }

        [data-testid="stButton"] {
            color: black; /* Couleur du texte par défaut */
            border: 1px solid transparent; /* Bordure transparente par défaut */
            border-radius: 0.700rem; /* Coins arrondis par défaut */
            transition: all 0.1s ease; /* Transition pour un effet plus doux */
        }

        [data-testid="stButton"]:hover {
            border: 1px solid #0059ff; /* Bordure bleue au survol */
            color: #0059ff; /* Texte bleu au survol */
        }

        [data-testid="stDecoration"] {background: #0059ff;}

        .st-emotion-cache-zy6yx3 {
            width: 100%;
            padding: 2.8rem 4rem 10rem;
            max-width: initial;
            min-width: auto;
        }
        </style>
        """,
        unsafe_allow_html=True
    )


if __name__ == "__main__":
    main()
