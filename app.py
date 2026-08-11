import os
import streamlit as st
from database import (
    init_db, 
    SessionLocal, 
    ChatSession, 
    ChatMessage, 
    delete_session, 
    rename_session,
    export_session_to_markdown
)
from auth import render_login
from agent import generate_agent_stream

st.set_page_config(page_title="Antigravity Console", page_icon="⚡", layout="wide")

# Ensure shared directory exists
SHARED_DIR = "./shared_data"
os.makedirs(SHARED_DIR, exist_ok=True)

init_db()
render_login()

# Sidebar Setup
st.sidebar.markdown("---")

# ==========================================
# FILE UPLOADER SECTION
# ==========================================
st.sidebar.subheader("📁 Upload Files for Agent")
uploaded_files = st.sidebar.file_uploader(
    "Choose files (PDF, TXT, Python, CSV, etc.)", 
    accept_multiple_files=True
)

if uploaded_files:
    for uploaded_file in uploaded_files:
        file_path = os.path.join(SHARED_DIR, uploaded_file.name)
        # Write file to ./shared_data so MCP server can access it
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
    st.sidebar.success(f"Saved {len(uploaded_files)} file(s) to agent workspace!")

st.sidebar.markdown("---")
st.sidebar.subheader("💬 Conversations")

db = SessionLocal()
sessions = db.query(ChatSession).order_by(ChatSession.created_at.desc()).all()

if st.sidebar.button("+ New Conversation", use_container_width=True):
    new_session = ChatSession(title="New Chat")
    db.add(new_session)
    db.commit()
    st.session_state.active_session_id = new_session.id
    st.rerun()

if "active_session_id" not in st.session_state:
    if sessions:
        st.session_state.active_session_id = sessions[0].id
    else:
        new_session = ChatSession(title="New Chat")
        db.add(new_session)
        db.commit()
        st.session_state.active_session_id = new_session.id

# Render conversation items with popovers
for s in sessions:
    col_btn, col_opts = st.sidebar.columns([0.8, 0.2])
    
    is_active = (s.id == st.session_state.active_session_id)
    btn_label = f"📌 {s.title[:16]}..." if is_active and len(s.title) > 16 else (s.title[:18] + "..." if len(s.title) > 18 else s.title)
    
    if col_btn.button(btn_label, key=f"session_{s.id}", use_container_width=True, type="primary" if is_active else "secondary"):
        st.session_state.active_session_id = s.id
        st.rerun()

    with col_opts.popover("⚙️"):
        st.caption("Manage Session")
        new_title = st.text_input("New Title", value=s.title, key=f"rename_input_{s.id}")
        if st.button("Save Title", key=f"save_title_{s.id}", use_container_width=True):
            if new_title.strip():
                rename_session(s.id, new_title.strip())
                st.rerun()

        st.markdown("---")
        if st.button("🗑️ Delete Session", key=f"del_{s.id}", type="primary", use_container_width=True):
            delete_session(s.id)
            if st.session_state.active_session_id == s.id:
                remaining_sessions = db.query(ChatSession).filter(ChatSession.id != s.id).all()
                if remaining_sessions:
                    st.session_state.active_session_id = remaining_sessions[0].id
                else:
                    del st.session_state["active_session_id"]
            st.rerun()

# Main Chat Dashboard View
current_session = db.query(ChatSession).filter(ChatSession.id == st.session_state.active_session_id).first()

if current_session:
    col_title, col_export = st.columns([0.75, 0.25])
    col_title.title(f"⚡ {current_session.title}")
    
    markdown_data = export_session_to_markdown(current_session.id)
    file_name = f"{current_session.title.lower().replace(' ', '_')}_history.md"
    
    col_export.download_button(
        label="📥 Export Markdown",
        data=markdown_data,
        file_name=file_name,
        mime="text/markdown",
        use_container_width=True
    )

    st.markdown("---")

    for msg in current_session.messages:
        with st.chat_message(msg.role):
            st.write(msg.content)

# Handle Chat Input
if prompt := st.chat_input("Ask your agent or ask it to read an uploaded file..."):
    with st.chat_message("user"):
        st.write(prompt)

    user_record = ChatMessage(session_id=current_session.id, role="user", content=prompt)
    db.add(user_record)

    if len(current_session.messages) == 0 or current_session.title == "New Chat":
        current_session.title = prompt[:30]
        db.commit()

    with st.chat_message("assistant"):
        full_response = ""

        def stream_and_capture():
            nonlocal full_response
            for chunk in generate_agent_stream(prompt):
                full_response += chunk
                yield chunk

        st.write_stream(stream_and_capture())

    agent_record = ChatMessage(session_id=current_session.id, role="assistant", content=full_response)
    db.add(agent_record)
    db.commit()

db.close()