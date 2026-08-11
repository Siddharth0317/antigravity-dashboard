import streamlit as st
from config import ADMIN_USERNAME, ADMIN_PASSWORD

def render_login():
    """Handles sidebar login authentication."""
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if not st.session_state.authenticated:
        st.sidebar.subheader("🔐 Private Login")
        username = st.sidebar.text_input("Username", value="")
        password = st.sidebar.text_input("Password", type="password", value="")
        
        if st.sidebar.button("Login"):
            if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.sidebar.error("Invalid username or password")
        st.stop()
    else:
        if st.sidebar.button("Logout"):
            st.session_state.authenticated = False
            st.rerun()