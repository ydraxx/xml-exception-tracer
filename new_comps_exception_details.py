from collections import defaultdict
import json
import os
import streamlit as st
from streamlit_extras.stylable_container import stylable_container

from config import xml_cfg, app_cfg
from func_llm_request import main as llm_request, print_code, replace_print_code, find_directory
from func_manage_json import JsonManager


manage_json = JsonManager()


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

        seen_ids = {} 
        for exception in group_exceptions:
            modified_exception = modify_exception_id_if_duplicate(exception, seen_ids)
            display_exception_details(modified_exception)  # Passer l'exception potentiellement modifiée


def modify_exception_id_if_duplicate(exception, seen_ids):
    """Modifie condition_id si une exception avec le même condition_id et condition_group existe déjà."""
    condition_id = exception['condition_id']
    condition_group = exception.get('condition_group', 'Autre')

    key = (condition_id, condition_group)

    if key in seen_ids:
        count = seen_ids[key] + 1
        new_condition_id = f"{condition_id}___{count}"
        exception['condition_id'] = new_condition_id
        seen_ids[key] = count
        
    else:
        seen_ids[key] = 0
    
    return exception


def display_exception_details(exception):
    """Display the details for a single exception."""
    
    with open(app_cfg["JSON_PROMPT"], 'r') as f:
                json_prompt = json.load(f)
    default_prompt = json_prompt["prompt_default"]

    model_names = ["gemini-2.0-flash-001", "claude-sonnet-4", "gpt-4o-mini-2024-07-18"]
    key_exception = exception['condition_group'] + '/' + exception['condition_id']
    exception_id = exception['condition_id'].split('___')[0]


    service_folder = exception_id.split('.')[0]
    service_folder, code_directory = find_directory(service_folder)

    with st.expander(f'**{exception_id}**'):
        st.write(f"**Group:** {exception['condition_group']}  \n**Type:** {exception['type']}  \n**Format:** {exception['format']}  \n**Path:** {exception['path']}")

        prompt_custom_key = f"prompt_custom_{key_exception}"
        if prompt_custom_key not in st.session_state:
            st.session_state[prompt_custom_key] = False

        text_area_visible_key = f"text_area_visible_{key_exception}"
        if text_area_visible_key not in st.session_state:
            st.session_state[text_area_visible_key] = False
            
        prompt_value_key = f"prompt_value_{key_exception}"
        if prompt_value_key not in st.session_state:
            st.session_state[prompt_value_key] = default_prompt

        model_name_key = f"model_name_selected_{key_exception}"
        if model_name_key not in st.session_state:
            st.session_state[model_name_key] = model_names[0]

        a, b, c = print_code(exception=exception_id)
        exception_code, exception_name, code_dep = a, b, c

        if not exception_code:
            disabled = True
        else:
            disabled = False

        show_code_key = f"show_code_{key_exception}"
        if show_code_key not in st.session_state:
            st.session_state[show_code_key] = False

        show_dep_key = f"show_dep_{key_exception}"
        if show_dep_key not in st.session_state:
            st.session_state[show_dep_key] = False


        # CASE WHEN CODE EXCEPTION IS NOT FOUND
        if not a:
            if code_directory:
                if not service_folder:
                    files_folder = os.path.join(xml_cfg['XML_PATH'], "codes", code_directory)
                else:
                    files_folder = os.path.join(xml_cfg['XML_PATH'], "codes", code_directory, service_folder)
                if os.path.exists(files_folder):
                    files = [f for f in os.listdir(files_folder)
                        if os.path.isfile(os.path.join(files_folder, f )) and 
                        os.path.join(files_folder, f ).endswith(".cc")]
                    files = [''] + files
                    replace_exception_name = st.selectbox(label="No exception code found. Select the right code.", 
                                                    options=files, 
                                                    key=f"disabled_{key_exception}_selectbox")
                    if replace_exception_name != '':
                        try:
                            exception_id = exception_id.split('.')[0] + '.' + replace_exception_name.split('_')[1].split('.')[0]
                        except:
                            exception_id = exception_id.split('.')[0]
                        exception_code, exception_name, code_dep = replace_print_code(exception=exception_id)
                if not exception_code:
                    disabled = True
                else:
                    disabled = False


        col1, col2, col3, col4 = st.columns(4) 

        # BUTTON CUSTOM PROMPT
        with col1:
            with stylable_container(
                key=f"prompt_{key_exception}_container", 
                css_styles=f"""
                .stButton > button {{
                    border-radius: 0.700rem;
                    transition: all 0.1s ease;
                    background-color: {"#0059ff" if st.session_state[prompt_custom_key] else "white"};
                    color: {"white" if st.session_state[prompt_custom_key] else "initial"};
                    
                }}
                .stButton > button: hover {{
                    border: 1px solid #0059ff;
                }}
                """
            ):
                if st.button(label='Custom prompt', key=f"prompt_{key_exception}_button",
                            use_container_width=True, disabled=disabled):
                    st.session_state[prompt_custom_key] = not st.session_state[prompt_custom_key]
                    st.session_state[show_code_key] = False
                    st.session_state[show_dep_key] = False
                    st.rerun()

        # BUTTON SHOW CODE
        with col2: 
            with stylable_container(
                key=f"dep_{key_exception}_button", 
                css_styles=f"""
                .stButton > button {{
                    border-radius: 0.700rem;
                    transition: all 0.1s ease;
                    background-color: {"#0059ff" if st.session_state[show_code_key] else "white"};
                    color: {"white" if st.session_state[show_code_key] else "initial"};
                    
                }}
                .stButton > button: hover {{
                    border: 1px solid #0059ff;
                }}
                """
            ):
                if st.button(label='Show exception code', key=f"dep_{key_exception}_button",
                            use_container_width=True, disabled=disabled):
                    st.session_state[show_code_key] = not st.session_state[show_code_key]
                    st.session_state[prompt_custom_key] = False
                    st.session_state[show_dep_key] = False
                    st.rerun()

        # BUTTON SHOW DEPENDENCIES
        with col3:
            with stylable_container(
                key=f"codes_{key_exception}_button", 
                css_styles=f"""
                .stButton > button {{
                    border-radius: 0.700rem;
                    transition: all 0.1s ease;
                    background-color: {"#0059ff" if st.session_state[show_dep_key] else "white"};
                    color: {"white" if st.session_state[show_dep_key] else "initial"};
                    
                }}
                .stButton > button: hover {{
                    border: 1px solid #0059ff;
                }}
                """
            ):
                if st.button(label='Show includes code', key=f"codes_{key_exception}_button",
                            use_container_width=True, disabled=disabled):
                    st.session_state[show_dep_key] = not st.session_state[show_dep_key]
                    st.session_state[prompt_custom_key] = False
                    st.session_state[show_code_key] = False
                    st.rerun()

        # BUTTON AI
        with col4:
            with stylable_container(
                key=f"AI_{key_exception}_button", 
                css_styles=f"""
                .stButton > button {{
                    border-radius: 0.700rem;
                    transition: all 0.1s ease;
                    background-color: {"#0059ff" if st.session_state.llm_results[key_exception] else "white"};
                    color: {"white" if st.session_state.llm_results[key_exception] else "initial"};
                    
                }}
                .stButton > button: hover {{
                    border: 1px solid #0059ff;
                }}
                """
            ):
                if st.button(label='Ask AI', key=f"AI_{key_exception}_button", 
                            use_container_width=True, disabled=disabled):
                    result = llm_request(exception=exception_id, 
                                        prompt_struct=st.session_state[prompt_value_key],
                                        model_name=st.session_state[model_name_key])
                    st.session_state.llm_results[key_exception] = result
                    st.session_state[prompt_custom_key] = False
                    st.session_state[show_code_key] = False
                    st.session_state[show_dep_key] = False
                    st.rerun()

        st.write('')
        # RESULT CUSTOM PROMPT
        if st.session_state[prompt_custom_key]:
            
            prompt_struct_key = f"input_{key_exception}"

            saved_prompt = manage_json.get_exception_value(module_name=code_directory,
                                                                condition_id=exception_id,
                                                                group=exception['condition_group'],
                                                                value_name='prompt')

            if saved_prompt:
                st.session_state[prompt_value_key] = saved_prompt
            
            st.write('')
            prompt1, prompt2, prompt3, prompt4 = st.columns(4)

            with prompt1:
                if st.button(label="Modify prompt", 
                             key=f"change_prompt_{key_exception}_button",
                             use_container_width=True):
                    st.session_state[text_area_visible_key] = not st.session_state[text_area_visible_key]
            
            
            st.session_state[model_name_key] = st.selectbox(
                label="Model:", 
                options=model_names, 
                key=f"model_name_{key_exception}"
            )

            if st.session_state[text_area_visible_key]:
                st.session_state[prompt_value_key] = st.text_area(label="Prompt:", value=st.session_state[prompt_value_key], key=prompt_struct_key)
            else:
                st.code(f"{st.session_state[prompt_value_key]}  \n\nPart 1:  \nFile: {exception_name}  \nCode:  \n{exception_code}  \n\nPart 2:  \nCode:  \n{code_dep}", 
                        language='markdown')
            
            with prompt2:
                if st.button(label="Save for later",
                             key=f"save_prompt_{key_exception}_button",
                             use_container_width=True):
                    manage_json.update_json_value(module_name=code_directory,
                                                    condition_id=exception_id,
                                                    group=exception['condition_group'],
                                                    to_change='prompt',
                                                    value=st.session_state[prompt_value_key])
                    st.session_state[prompt_value_key] = saved_prompt
                    st.session_state[text_area_visible_key] = None
                    st.rerun()

        # RESULT SHOW CODE
        if st.session_state[show_code_key]:
            st.code(f"File: {exception_name}  \nCode:  \n{exception_code}", language='cpp')

        # RESULT SHOW DEP
        if st.session_state[show_dep_key]:
            st.code(code_dep, language='cpp')

        # IA RESULT
        ai_result = None 

        if code_directory:
            existing_explanation = manage_json.get_exception_value(module_name=code_directory,
                                                                    condition_id=exception_id,
                                                                    group=exception['condition_group'],
                                                                    value_name='ai_explanation')
        else:
            existing_explanation = None

        # Initialize session state for existing_explanation, only if it doesn't exist
        if f"existing_explanation_{key_exception}" not in st.session_state:
            st.session_state[f"existing_explanation_{key_exception}"] = existing_explanation

        # Sync ai_result with existing explanation in session state
        ai_result = st.session_state[f"existing_explanation_{key_exception}"]

        # If no explanation exists in manage_json, try to load from st.session_state.llm_results
        if ai_result is None and key_exception in st.session_state.llm_results:
            ai_result = st.session_state.llm_results[key_exception]


        if ai_result:
            if (st.session_state.llm_results[key_exception] and 
                st.session_state[f"existing_explanation_{key_exception}"] and
                st.session_state[f"existing_explanation_{key_exception}"] != st.session_state.llm_results[key_exception]):
                st.write('**Select which response you want to keep.**')
                st.write("Saved explanation.")
                button_choice_1 = st.checkbox(st.session_state[f"existing_explanation_{key_exception}"], key=f"choice1_{key_exception}_button")
                st.divider()
                st.write("New explanation.")
                button_choice_2 = st.checkbox(st.session_state.llm_results[key_exception], key=f"choice2_{key_exception}_button")

                if button_choice_1:
                    st.session_state.llm_results[key_exception] = st.session_state[f"existing_explanation_{key_exception}"]
                    st.rerun()
                elif button_choice_2:
                    st.session_state[f"existing_explanation_{key_exception}"] = st.session_state.llm_results[key_exception]
                    st.rerun()

            # If ai_result is not None, you might want to set a default value or skip the rest of the code
            else:
                # Initialize a state to track if the explanation is being modified
                if f"is_modifying_{key_exception}" not in st.session_state:
                    st.session_state[f"is_modifying_{key_exception}"] = False

                st.write('')
                col1ai, col6ai, col7ai, col8ai = st.columns(4)

                # Display ai_result by default IF the text area is not displayed
                if not st.session_state[f"is_modifying_{key_exception}"]:
                    st.write(ai_result)

                with col1ai:
                    # Modify button clicked
                    modify_button = st.button(label='Modify', key=f"modify_explanation{key_exception}_button",
                                            use_container_width=True)

                    # Toggle the modification state if Modify is clicked
                    if modify_button:
                        st.session_state[f"is_modifying_{key_exception}"] = not st.session_state[
                            f"is_modifying_{key_exception}"]
                        st.rerun()  # Rerun to update the UI

                # Display the text area if modification is in progress
                if st.session_state[f"is_modifying_{key_exception}"]:
                    ai_result = st.text_area(label='AI explanation',
                                            key=f"modify_explanation{key_exception}_text_area",
                                            value=ai_result)  # Update ai_result with the text area value

                with col6ai:
                    # Save button (always visible)
                    save_button = st.button(label='Validate', key=f"save_explanation{key_exception}_button",
                                            use_container_width=True)

                    # Save action (always performed if Save button is clicked AND text area is visible)
                    if save_button:
                        manage_json.update_json_value(module_name=code_directory,
                                                        condition_id=exception_id,
                                                        group=exception['condition_group'],
                                                        to_change='ai_explanation',
                                                        value=ai_result)

                        # Update the session state with the new explanation
                        st.session_state[f"existing_explanation_{key_exception}"] = ai_result
                        st.session_state.llm_results[key_exception] = None
                        st.session_state[f"is_modifying_{key_exception}"] = False  # Hide the text area after saving
                        st.rerun()

                with col7ai:
                    confluence_button = st.button(label='Send to Confluence',
                                                key=f"confluence_{key_exception}_button",
                                                use_container_width=True,
                                                disabled=not st.session_state[
                                                    f"existing_explanation_{key_exception}"])

                    if confluence_button:
                        # rien pour l'instant
                        print('ok')
