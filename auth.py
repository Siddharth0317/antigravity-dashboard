import time
import streamlit as st
from database import authenticate_user, create_user

MAX_FAILED_ATTEMPTS = 5
LOCKOUT_TIME_SECONDS = 60

def render_login():
    """Handles sidebar authentication with rate limiting and user account management."""
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if "failed_attempts" not in st.session_state:
        st.session_state.failed_attempts = 0

    if "lockout_until" not in st.session_state:
        st.session_state.lockout_until = 0

    if not st.session_state.authenticated:
        st.sidebar.subheader("🔐 Console Login")

        # Rate Limiting: Lockout check
        current_time = time.time()
        if current_time < st.session_state.lockout_until:
            remaining_secs = int(st.session_state.lockout_until - current_time)
            st.sidebar.error(f"⛔ Account locked due to repeated failed attempts. Retry in {remaining_secs}s.")
            st.stop()

        tab_login, tab_register = st.sidebar.tabs(["Login", "Register User"])

        with tab_login:
            username = st.text_input("Username", key="login_username")
            password = st.text_input("Password", type="password", key="login_password")

            if st.button("Sign In", use_container_width=True, type="primary"):
                if not username or not password:
                    st.sidebar.error("Please enter both username and password.")
                else:
                    user_data = authenticate_user(username, password)
                    if user_data:
                        st.session_state.authenticated = True
                        st.session_state.user = user_data
                        st.session_state.failed_attempts = 0
                        st.session_state.lockout_until = 0
                        st.rerun()
                    else:
                        st.session_state.failed_attempts += 1
                        if st.session_state.failed_attempts >= MAX_FAILED_ATTEMPTS:
                            st.session_state.lockout_until = time.time() + LOCKOUT_TIME_SECONDS
                            st.sidebar.error("⛔ Account locked for 60s due to repeated failed attempts.")
                        else:
                            attempts_left = MAX_FAILED_ATTEMPTS - st.session_state.failed_attempts
                            st.sidebar.error(f"Invalid credentials. ({attempts_left} attempts left)")
        
        with tab_register:
            reg_username = st.text_input("New Username", key="reg_username")
            reg_password = st.text_input("New Password", type="password", key="reg_password")
            confirm_password = st.text_input("Confirm Password", type="password", key="reg_confirm")

            if st.button("Create Account", use_container_width=True):
                if not reg_username or not reg_password:
                    st.sidebar.error("Username and password cannot be empty.")
                elif len(reg_password) < 6:
                    st.sidebar.error("Password must be at least 6 characters long.")
                elif reg_password != confirm_password:
                    st.sidebar.error("Passwords do not match.")
                else:
                    success, msg = create_user(reg_username, reg_password)
                    if success:
                        st.sidebar.success(msg + " Please sign in.")
                    else:
                        st.sidebar.error(msg)
        
        st.stop()
    else:
        user = st.session_state.get("user", {})
        username_display = user.get("username", "User")
        role_display = user.get("role", "user")
        
        st.sidebar.caption(f"Logged in as: **{username_display}** (`{role_display}`)")
        if st.sidebar.button("Logout", use_container_width=True):
            st.session_state.authenticated = False
            st.session_state.user = None
            st.rerun()