import streamlit as st

def init_session_var(key, default):
    if key not in st.session_state:
        st.session_state[key] = default
