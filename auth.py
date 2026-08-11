import time
import streamlit as st
from config import ADMIN_PASSWORD

MAX_FAILED_ATTEMPTS = 5
LOCKOUT_TIME_SECONDS = 60

def render_login():
    """Single-user passcode authentication with rate-limiting security."""
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if "failed_attempts" not in st.session_state:
        st.session_state.failed_attempts = 0

    if "lockout_until" not in st.session_state:
        st.session_state.lockout_until = 0

    if not st.session_state.authenticated:
        st.sidebar.subheader("🔐 Private Access")

        # Rate Limiting: Lockout check
        current_time = time.time()
        if current_time < st.session_state.lockout_until:
            remaining_secs = int(st.session_state.lockout_until - current_time)
            st.sidebar.error(f"⛔ Console locked out. Try again in {remaining_secs}s.")
            st.stop()

        with st.sidebar.form("login_form", clear_on_submit=False):
            password = st.text_input("Enter Passcode", type="password", key="master_password")
            submitted = st.form_submit_button("Unlock Console", use_container_width=True, type="primary")

        if submitted:
            if not ADMIN_PASSWORD:
                st.sidebar.error("Please set `ADMIN_PASSWORD=your_password` in `.env` file.")
            elif password == ADMIN_PASSWORD:
                st.session_state.authenticated = True
                st.session_state.failed_attempts = 0
                st.session_state.lockout_until = 0
                st.rerun()
            else:
                st.session_state.failed_attempts += 1
                if st.session_state.failed_attempts >= MAX_FAILED_ATTEMPTS:
                    st.session_state.lockout_until = time.time() + LOCKOUT_TIME_SECONDS
                    st.sidebar.error("⛔ Console locked for 60s due to repeated failed attempts.")
                else:
                    attempts_left = MAX_FAILED_ATTEMPTS - st.session_state.failed_attempts
                    st.sidebar.error(f"Incorrect passcode. ({attempts_left} attempts left)")

        st.stop()
    else:
        if st.sidebar.button("🔒 Lock Console", use_container_width=True):
            st.session_state.authenticated = False
            st.rerun()