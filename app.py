import os
import time
import asyncio
import streamlit as st
from database import (
    init_db, 
    SessionLocal, 
    ChatSession, 
    ChatMessage, 
    delete_session, 
    rename_session,
    export_session_to_markdown,
    export_session_to_json,
    log_analytics_event,
    get_analytics_summary
)
from auth import render_login
from agent import generate_agent_stream
from scheduler import start_scheduler, stop_scheduler, scheduler, run_daily_summary_job

st.set_page_config(
    page_title="Gemini Antigravity Console", 
    page_icon="✨", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==========================================
# GOOGLE GEMINI DARK THEME AESTHETIC SYSTEM
# ==========================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Google+Sans:wght@400;500;700&display=swap');

    /* Global Body & Deep Gemini Dark Theme */
    html, body, .stApp {
        background-color: #131314 !important;
        font-family: 'Google Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
        color: #e3e3e3 !important;
    }

    /* Google Gemini Dark Sidebar (#1e1f20) */
    [data-testid="stSidebar"] {
        background-color: #1e1f20 !important;
        border-right: 1px solid #2d2f31 !important;
    }

    /* Metric Cards - Dark Glassmorphism */
    div[data-testid="metric-container"] {
        background-color: #1e1f20 !important;
        border: 1px solid #2d2f31 !important;
        border-radius: 16px !important;
        padding: 14px 18px !important;
        box-shadow: 0 4px 14px rgba(0, 0, 0, 0.4) !important;
    }

    div[data-testid="stMetricValue"] {
        font-size: 1.5rem !important;
        font-weight: 700 !important;
        color: #a8c7fa !important;
    }

    div[data-testid="stMetricLabel"] {
        font-size: 0.85rem !important;
        color: #c4c7c5 !important;
        font-weight: 500 !important;
    }

    /* Primary Gemini Glowing Pill Buttons */
    .stButton > button {
        background: linear-gradient(135deg, #1a73e8 0%, #0b57d0 100%) !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: 24px !important;
        font-weight: 500 !important;
        padding: 0.5rem 1.25rem !important;
        transition: all 0.2s ease !important;
        box-shadow: 0 2px 8px rgba(26, 115, 232, 0.3) !important;
    }

    .stButton > button:hover {
        box-shadow: 0 4px 16px rgba(168, 199, 250, 0.4) !important;
        transform: translateY(-1px) !important;
    }

    /* Secondary Sidebar Conversation Pills */
    button[kind="secondary"] {
        background: #282a2c !important;
        color: #e3e3e3 !important;
        border: 1px solid #37393b !important;
        border-radius: 20px !important;
        box-shadow: none !important;
    }

    button[kind="secondary"]:hover {
        background: #37393b !important;
        color: #a8c7fa !important;
    }

    /* Inputs & Search Input Fields */
    .stTextInput > div > div > input {
        border-radius: 12px !important;
        border: 1px solid #444746 !important;
        background-color: #131314 !important;
        color: #e3e3e3 !important;
    }

    .stTextInput > div > div > input:focus {
        border-color: #a8c7fa !important;
        box-shadow: 0 0 0 2px rgba(168, 199, 250, 0.2) !important;
    }

    /* Gemini Floating Chat Capsule Input Bar */
    .stChatInput > div {
        border-radius: 28px !important;
        border: 1px solid #444746 !important;
        background-color: #1e1f20 !important;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.5) !important;
        padding: 6px 12px !important;
    }

    .stChatInput > div:focus-within {
        border-color: #a8c7fa !important;
        box-shadow: 0 4px 24px rgba(168, 199, 250, 0.25) !important;
    }

    /* Gemini Chat Messages Container Cards */
    div[data-testid="stChatMessage"] {
        background-color: #1e1f20 !important;
        border: 1px solid #2d2f31 !important;
        border-radius: 18px !important;
        padding: 14px 18px !important;
        margin-bottom: 12px !important;
        box-shadow: 0 2px 10px rgba(0, 0, 0, 0.25) !important;
    }

    /* Gemini Header Badge */
    .gemini-dark-badge {
        background: linear-gradient(135deg, rgba(168, 199, 250, 0.15) 0%, rgba(26, 115, 232, 0.15) 100%);
        border: 1px solid rgba(168, 199, 250, 0.3);
        color: #a8c7fa;
        padding: 6px 16px;
        border-radius: 20px;
        font-size: 0.85rem;
    /* Mobile Responsive Optimizations for Phone Web Browsers */
    @media (max-width: 768px) {
        .block-container {
            padding-left: 0.6rem !important;
            padding-right: 0.6rem !important;
            padding-top: 0.8rem !important;
        }

        /* Stacking cards on mobile screens */
        div[data-testid="column"] {
            margin-bottom: 6px !important;
        }

        /* Responsive touch targets for finger taps */
        .stButton > button {
            min-height: 46px !important;
            font-size: 0.95rem !important;
            width: 100% !important;
        }

        .stChatInput > div {
            border-radius: 22px !important;
            padding: 4px 6px !important;
        }

        h2 {
            font-size: 1.35rem !important;
        }
    }
</style>
""", unsafe_allow_html=True)

# Ensure shared directory exists
SHARED_DIR = "./shared_data"
os.makedirs(SHARED_DIR, exist_ok=True)

init_db()
render_login()

# ==========================================
# SIDEBAR CONFIGURATION & TOOLS
# ==========================================

st.sidebar.markdown("""
<div style="text-align: center; padding: 10px 0;">
    <h2 style="color: #a8c7fa; margin: 0; font-size: 1.5rem;">✨ AI Agent</h2>
    <span style="color: #c4c7c5; font-size: 0.85rem; font-weight: 500;">Welcome, <b>Siddharth</b> 👋</span>
</div>
""", unsafe_allow_html=True)

st.sidebar.markdown("---")

api_key_env = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or os.getenv("API_KEY")
if not api_key_env:
    st.sidebar.warning("⚠️ `GEMINI_API_KEY` missing in `.env` file.")

# 🤖 Model Selector
st.sidebar.subheader("🤖 Model Engine")
selected_model = st.sidebar.selectbox(
    "Select Model Engine",
    ["Default (Auto)", "gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro", "gemini-2.5-flash"],
    index=0,
    help="Default (Auto): Automatically uses the best default model supported by your Gemini API key."
)

st.sidebar.markdown("---")

# 🎭 System Persona & Instructions Customizer
st.sidebar.subheader("🎭 Persona Customizer")

preset_personas = {
    "🤖 Default Agent": (
        "You are an autonomous AI assistant powered by Google Antigravity. "
        "You have access to a filesystem MCP server pointing to the './shared_data' directory. "
        "Use your tools to inspect and process files when requested."
    ),
    "🐍 Senior Python Developer": (
        "You are an expert Senior Python Developer & Software Architect. "
        "Provide production-grade, highly efficient, well-documented code with type hints and robust error handling."
    ),
    "📊 Senior Data Analyst": (
        "You are a Senior Data Analyst and Business Intelligence expert. "
        "Analyze workspace files, synthesize key insights, generate clear metrics, and summarize trends concisely."
    ),
    "🛡️ Cybersecurity Auditor": (
        "You are a Lead Cybersecurity & Infrastructure Security Auditor. "
        "Inspect codebase and workspace files for security vulnerabilities, secrets leakage, and hardcoded credentials."
    ),
    "✍️ Technical Writer": (
        "You are an Executive Technical Writer and Documentation Specialist. "
        "Format reports with clean Markdown headers, bullet points, executive summaries, and clear action items."
    )
}

selected_persona_name = st.sidebar.selectbox(
    "Choose Preset Persona",
    list(preset_personas.keys()),
    index=0
)

custom_instructions = st.sidebar.text_area(
    "Edit System Instructions",
    value=preset_personas[selected_persona_name],
    height=110,
    help="Modify these instructions to change how the agent behaves and responds."
)

st.sidebar.markdown("---")

# 📁 Workspace File Manager
st.sidebar.subheader("📁 Workspace Files")

uploaded_files = st.sidebar.file_uploader(
    "Upload Documents (PDF, TXT, CSV, PY)", 
    accept_multiple_files=True
)

if uploaded_files:
    for uploaded_file in uploaded_files:
        file_path = os.path.join(SHARED_DIR, uploaded_file.name)
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
    st.sidebar.success(f"Uploaded {len(uploaded_files)} file(s)!")
    st.rerun()

existing_files = os.listdir(SHARED_DIR)
if existing_files:
    with st.sidebar.expander(f"📂 View Files ({len(existing_files)})"):
        for fname in existing_files:
            fpath = os.path.join(SHARED_DIR, fname)
            fsize_kb = round(os.path.getsize(fpath) / 1024, 1)
            
            c_name, c_del = st.columns([0.75, 0.25])
            c_name.caption(f"📄 **{fname}** ({fsize_kb} KB)")
            
            if c_del.button("🗑️", key=f"delfile_{fname}"):
                os.remove(fpath)
                st.rerun()
            
            if fname.endswith(('.txt', '.csv', '.json', '.py', '.md')):
                try:
                    with open(fpath, 'r', encoding='utf-8', errors='ignore') as pf:
                        snippet = pf.read(250)
                    st.code(snippet[:180] + ("..." if len(snippet) > 180 else ""), language="text")
                except Exception:
                    pass
else:
    st.sidebar.caption("Workspace folder empty (`./shared_data`)")

st.sidebar.markdown("---")

# ⏰ Autonomous Background Scheduler Control
st.sidebar.subheader("⏰ Background Scheduler")

enable_scheduler = st.sidebar.toggle(
    "Enable Background Cron Tasks", 
    value=st.session_state.get("bg_scheduler_enabled", False),
    help="When enabled, the background worker automatically runs daily workspace briefings."
)

if enable_scheduler:
    if not scheduler.running:
        start_scheduler()
    st.session_state.bg_scheduler_enabled = True
    st.sidebar.caption("Status: 🟢 **Active (Cron: Daily 8:00 AM)**")
else:
    if scheduler.running:
        stop_scheduler()
    st.session_state.bg_scheduler_enabled = False
    st.sidebar.caption("Status: 🔴 **Disabled (On-Demand Only)**")

if st.sidebar.button("⚡ Run Briefing Now", use_container_width=True):
    with st.spinner("Agent is inspecting files & compiling briefing..."):
        run_daily_summary_job()
    st.sidebar.success("Briefing updated!")
    st.rerun()

st.sidebar.markdown("---")

# 💬 Search & Conversation Manager
st.sidebar.subheader("💬 Conversations")

db = SessionLocal()
sessions = db.query(ChatSession).order_by(ChatSession.created_at.desc()).all()

search_query = st.sidebar.text_input("🔍 Search History", placeholder="Filter by title...")
filtered_sessions = [
    s for s in sessions 
    if not search_query or search_query.lower() in s.title.lower()
]

if st.sidebar.button("+ New Chat", use_container_width=True, type="primary"):
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

# Render Session Items
for s in filtered_sessions:
    col_btn, col_opts = st.sidebar.columns([0.8, 0.2])
    
    is_active = (s.id == st.session_state.active_session_id)
    btn_label = f"💬 {s.title[:16]}..." if is_active and len(s.title) > 16 else (s.title[:18] + "..." if len(s.title) > 18 else s.title)
    
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

if "pending_approval" not in st.session_state:
    st.session_state.pending_approval = None

# Show welcome toast on session login
if "welcome_shown" not in st.session_state:
    st.toast("👋 Welcome back, Siddharth!", icon="✨")
    st.session_state.welcome_shown = True

# ==========================================
# MAIN DASHBOARD VIEW & METRICS BAR
# ==========================================

current_session = db.query(ChatSession).filter(ChatSession.id == st.session_state.get("active_session_id")).first()

if current_session:
    col_welcome, col_export = st.columns([0.65, 0.35])
    with col_welcome:
        st.markdown('<div class="gemini-dark-badge">✨ Google Antigravity &bull; Gemini Dark Console</div>', unsafe_allow_html=True)
        st.markdown('<h2 style="color: #a8c7fa; margin-top: -6px; margin-bottom: 2px; font-weight: 700; font-size: 1.8rem;">👋 Welcome back, Siddharth</h2>', unsafe_allow_html=True)
        st.title(f"{current_session.title}")

    markdown_data = export_session_to_markdown(current_session.id)
    json_data = export_session_to_json(current_session.id)
    slug_title = current_session.title.lower().replace(' ', '_').replace('/', '_')

    with col_export.popover("📥 Export Session Log", use_container_width=True):
        st.caption("Download Conversation Record")
        st.download_button(
            label="📝 Download as Markdown (.md)",
            data=markdown_data,
            file_name=f"{slug_title}.md",
            mime="text/markdown",
            use_container_width=True
        )
        st.download_button(
            label="📦 Download as JSON (.json)",
            data=json_data,
            file_name=f"{slug_title}.json",
            mime="application/json",
            use_container_width=True
        )

    # Top Metric Cards (Gemini Dark Style)
    m1, m2, m3 = st.columns(3)
    total_files = len(os.listdir(SHARED_DIR))
    total_kb = sum(os.path.getsize(os.path.join(SHARED_DIR, f)) for f in os.listdir(SHARED_DIR)) // 1024 if total_files else 0
    
    m1.metric("🤖 Active Engine", selected_model, "Connected 🟢")
    m2.metric("📁 Workspace Storage", f"{total_files} files", f"{total_kb} KB total")
    m3.metric("💬 Saved Sessions", f"{len(sessions)} total", f"Active: #{current_session.id}")

    # Analytics & System Diagnostics Panel
    with st.expander("📊 System Analytics & Diagnostics"):
        analytics = get_analytics_summary()
        a1, a2, a3, a4 = st.columns(4)
        a1.metric("⏱️ Avg Latency", f"{analytics['avg_latency']}s")
        a2.metric("💬 Total Queries", f"{analytics['total_queries']}")
        a3.metric("🪙 Tokens Processed", f"{analytics['total_tokens']:,}")
        a4.metric("🛠️ Tool Executions", f"{analytics['total_tool_calls']}")

        if analytics['recent_logs']:
            st.caption("Recent Query Execution Log:")
            st.dataframe(analytics['recent_logs'], use_container_width=True)
        else:
            st.caption("No diagnostic logs yet. Start chatting with the agent to track live latency & token stats!")

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

    # Display Chat Messages
    for msg in current_session.messages:
        with st.chat_message(msg.role):
            st.write(msg.content)
            if msg.role == "assistant":
                import html as html_lib
                escaped_text = html_lib.escape(msg.content.replace("\n", " ").replace("'", "\\'"))
                tts_html = f"""
                <div style="margin-top: 6px;">
                    <button onclick="playTTS()" ontouchend="playTTS()" style="background: #282a2c; color: #a8c7fa; border: 1px solid #37393b; border-radius: 16px; padding: 6px 14px; font-size: 0.85rem; cursor: pointer; min-height: 36px;">
                        🔊 Read Aloud
                    </button>
                    <button onclick="stopTTS()" ontouchend="stopTTS()" style="background: #282a2c; color: #f28b82; border: 1px solid #37393b; border-radius: 16px; padding: 6px 14px; font-size: 0.85rem; cursor: pointer; margin-left: 6px; min-height: 36px;">
                        ⏹️ Stop Audio
                    </button>
                </div>
                <script>
                function playTTS() {{
                    const msg = new SpeechSynthesisUtterance('{escaped_text}');
                    window.speechSynthesis.cancel();
                    window.speechSynthesis.speak(msg);
                }}
                function stopTTS() {{
                    window.speechSynthesis.cancel();
                }}
                </script>
                """
                st.components.v1.html(tts_html, height=50)

    # Voice Dictation Mic Tool
    with st.expander("🎙️ Voice Dictation Mic Input"):
        dictation_html = """
        <div style="background: #1e1f20; border: 1px solid #37393b; border-radius: 14px; padding: 12px; font-family: sans-serif;">
            <div style="display: flex; flex-direction: column; gap: 8px;">
                <button id="mic_btn" onclick="startDictation()" ontouchend="startDictation()" style="background: linear-gradient(135deg, #1a73e8, #0b57d0); color: white; border: none; border-radius: 20px; padding: 10px 20px; font-weight: 500; font-size: 0.95rem; cursor: pointer; min-height: 44px; width: 100%;">
                    🎙️ Start Mobile Dictation
                </button>
                <span id="mic_status" style="color: #c4c7c5; font-size: 0.9rem; text-align: center;">Tap button & speak into microphone...</span>
            </div>
            <div id="dictation_output" style="margin-top: 10px; color: #a8c7fa; font-size: 0.95rem; font-style: italic; min-height: 22px; word-break: break-word;"></div>
        </div>

        <script>
        function startDictation() {
            const status = document.getElementById('mic_status');
            const output = document.getElementById('dictation_output');
            
            if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
                status.innerText = '⚠️ Speech recognition not supported on this mobile browser.';
                return;
            }
            
            const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
            const recognition = new SpeechRecognition();
            recognition.continuous = false;
            recognition.interimResults = true;
            recognition.lang = 'en-US';
            
            status.innerText = '🎙️ Listening... Speak now!';
            recognition.start();
            
            recognition.onresult = function(event) {
                let transcript = '';
                for (let i = event.resultIndex; i < event.results.length; ++i) {
                    transcript += event.results[i][0].transcript;
                }
                output.innerText = transcript;
            };
            
            recognition.onerror = function(event) {
                status.innerText = '⚠️ Dictation error: ' + event.error;
            };
            
            recognition.onend = function() {
                status.innerText = '✅ Speech captured!';
            };
        }
        </script>
        """
        st.components.v1.html(dictation_html, height=130)

    # Quick Action Prompt Chips
    st.caption("⚡ **Quick Actions:**")
    q1, q2, q3, q4 = st.columns(4)
    
    preset_prompt = None
    if q1.button("📋 Workspace Audit", use_container_width=True, key="chip_audit"):
        preset_prompt = "Inspect all files in `./shared_data` and provide a detailed workspace summary report."
    if q2.button("🔍 Code Quality Review", use_container_width=True, key="chip_code"):
        preset_prompt = "Perform a code quality audit on Python and script files in `./shared_data`."
    if q3.button("📝 Executive Briefing", use_container_width=True, key="chip_brief"):
        preset_prompt = "Compile a clean executive briefing covering workspace health, file contents, and recommended actions."
    if q4.button("⚡ Refactor & Optimize", use_container_width=True, key="chip_opt"):
        preset_prompt = "Analyze files in `./shared_data` and suggest performance optimizations or code refactoring."

    # Chat Input Box (Floating Gemini Capsule)
    chat_prompt = st.chat_input(f"Ask AI Agent ({selected_model}) or request file inspection...")
    prompt = preset_prompt or chat_prompt

    if prompt:
        with st.chat_message("user"):
            st.write(prompt)

        user_record = ChatMessage(session_id=current_session.id, role="user", content=prompt)
        db.add(user_record)

        if len(current_session.messages) == 0 or current_session.title == "New Chat":
            current_session.title = prompt[:30]
            db.commit()

        start_time = time.time()

        with st.chat_message("assistant"):
            response_chunks = []

            def stream_and_capture():
                try:
                    for chunk in generate_agent_stream(prompt, model_name=selected_model, system_instruction=custom_instructions):
                        response_chunks.append(chunk)
                        yield chunk
                except Exception as e:
                    err_msg = str(e)
                    if "API key" in err_msg or "AntigravityValidationError" in type(e).__name__:
                        st.error("🔑 **API Key Error**: Please set `GEMINI_API_KEY=your_key` in your `.env` file.")
                    else:
                        st.error(f"⚠️ Error: {e}")

            st.write_stream(stream_and_capture())

        latency = time.time() - start_time
        full_response = "".join(response_chunks)
        agent_record = ChatMessage(session_id=current_session.id, role="assistant", content=full_response)
        db.add(agent_record)
        db.commit()

        # Record Analytics Diagnostics Event
        log_analytics_event(
            session_id=current_session.id,
            prompt=prompt,
            model_name=selected_model,
            latency=latency,
            response_text=full_response
        )

db.close()