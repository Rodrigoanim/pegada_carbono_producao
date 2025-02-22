import streamlit as st
from paginas.monitor import clear_log_flags

def logout():
    """Realiza o logout do usuário"""
    clear_log_flags()
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()
