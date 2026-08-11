import asyncio
import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from database import SessionLocal, ChatSession, ChatMessage
from agent import stream_antigravity_agent

def run_daily_summary_job():
    """
    Background task that inspects files in ./shared_data
    and saves a compiled summary briefing into SQLite.
    """
    print("[Cron Job] Starting daily autonomous agent briefing task...")

    db = SessionLocal()
    
    # Get or create dedicated briefing session
    session = db.query(ChatSession).filter(ChatSession.title == "🤖 Daily Automated Briefings").first()
    if not session:
        session = ChatSession(title="🤖 Daily Automated Briefings")
        db.add(session)
        db.commit()
        db.refresh(session)

    # Customized automated prompt
    custom_prompt = (
        "Perform an automated workspace briefing:\n\n"
        "1. **Local Workspace Audit:** Use your filesystem tools to inspect the './shared_data' directory. "
        "List any files found, read brief contents of recent text/PDF/CSV files, and provide a clear summary.\n"
        "2. **System Status Report:** Summarize the workspace health and any key insights from uploaded documents.\n\n"
        "Format the final output clearly with markdown headers."
    )

    # Record trigger entry
    user_msg = ChatMessage(session_id=session.id, role="user", content=f"[Automated Briefing Trigger]\n{custom_prompt}")
    db.add(user_msg)
    db.commit()

    # Execute agent stream asynchronously
    response_chunks = []

    async def execute_task():
        async for chunk in stream_antigravity_agent(custom_prompt):
            response_chunks.append(chunk)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(execute_task())
    loop.close()

    full_response = "".join(response_chunks)

    # Save agent response
    agent_msg = ChatMessage(session_id=session.id, role="assistant", content=full_response)
    db.add(agent_msg)
    db.commit()
    db.close()

    print("[Cron Job] Daily autonomous agent briefing task completed!")

scheduler = BackgroundScheduler()

def start_scheduler():
    if not scheduler.running:
        # Set to run daily at 8:00 AM
        scheduler.add_job(
            run_daily_summary_job, 
            trigger='cron', 
            hour=8, 
            minute=0, 
            id='daily_tech_summary',
            replace_existing=True
        )
        scheduler.start()
        print("[Scheduler] Background cron worker active.")