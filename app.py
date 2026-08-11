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
from scheduler import start_scheduler, scheduler, run_daily_summary_job

st.set_page_config(page_title="Antigravity Console", page_icon="⚡", layout="wide")

# Ensure shared directory exists
SHARED_DIR = "./shared_data"
os.makedirs(SHARED_DIR, exist_ok=True)

init_db()
render_login()

# Initialize APScheduler background worker
start_scheduler()

# Sidebar Setup
st.sidebar.markdown("---")

api_key_env = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or os.getenv("API_KEY")
if not api_key_env:
    st.sidebar.warning("⚠️ `GEMINI_API_KEY` missing in `.env` file.")

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

# ==========================================
# AUTONOMOUS SCHEDULER SECTION
# ==========================================
st.sidebar.subheader("⏰ Autonomous Scheduler")
if scheduler.running:
    st.sidebar.caption("Status: 🟢 **Running** (APScheduler)")
else:
    st.sidebar.caption("Status: 🔴 **Stopped**")

if st.sidebar.button("⚡ Run Daily Briefing Now", use_container_width=True):
    with st.spinner("Agent is inspecting local files & compiling briefing..."):
        run_daily_summary_job()
    st.sidebar.success("Briefing updated! Check the '🤖 Daily Automated Briefings' session.")
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.subheader("💬 Conversations")

db = SessionLocal()

current_user = st.session_state.get("user")
user_id = current_user.get("id") if current_user else None

if current_user and current_user.get("role") != "admin":
    sessions = db.query(ChatSession).filter(
        (ChatSession.user_id == user_id) | (ChatSession.user_id == None)
    ).order_by(ChatSession.created_at.desc()).all()
else:
    sessions = db.query(ChatSession).order_by(ChatSession.created_at.desc()).all()

if st.sidebar.button("+ New Conversation", use_container_width=True):
    new_session = ChatSession(title="New Chat", user_id=user_id)
    db.add(new_session)
    db.commit()
    st.session_state.active_session_id = new_session.id
    st.rerun()

if "active_session_id" not in st.session_state:
    if sessions:
        st.session_state.active_session_id = sessions[0].id
    else:
        new_session = ChatSession(title="New Chat", user_id=user_id)
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

# Initialize approval session state
if "pending_approval" not in st.session_state:
    st.session_state.pending_approval = None

# Main Chat Dashboard View
current_session = db.query(ChatSession).filter(ChatSession.id == st.session_state.get("active_session_id")).first()

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

    # ==========================================
    # HUMAN-IN-THE-LOOP APPROVAL BANNER
    # ==========================================
    if st.session_state.get("pending_approval") and st.session_state.pending_approval.get("status") == "pending":
        approval_data = st.session_state.pending_approval
        
        st.warning(f"⚠️ **PERMISSION REQUIRED**: The agent is requesting to execute `{approval_data['tool_name']}`")
        
        with st.expander("🔍 View Action Details", expanded=True):
            st.code(approval_data["details"], language="text")

        col_approve, col_reject, _ = st.columns([0.2, 0.2, 0.6])
        
        if col_approve.button("✅ Approve Action", type="primary", use_container_width=True, key="btn_approve_banner"):
            st.session_state.pending_approval["status"] = "approved"
            st.rerun()

        if col_reject.button("❌ Reject Action", use_container_width=True, key="btn_reject_banner"):
            st.session_state.pending_approval["status"] = "rejected"
            st.rerun()

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
            response_chunks = []

            def stream_and_capture():
                try:
                    for chunk in generate_agent_stream(prompt):
                        response_chunks.append(chunk)
                        yield chunk
                except Exception as e:
                    err_msg = str(e)
                    if "API key" in err_msg or "AntigravityValidationError" in type(e).__name__:
                        st.error("🔑 **API Key Error**: Please add `GEMINI_API_KEY=your_api_key` in your `.env` file and save it.")
                    else:
                        st.error(f"⚠️ Error: {e}")

            st.write_stream(stream_and_capture())

        full_response = "".join(response_chunks)
        agent_record = ChatMessage(session_id=current_session.id, role="assistant", content=full_response)
        db.add(agent_record)
        db.commit()

db.close()