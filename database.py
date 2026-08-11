import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from config import DATABASE_URL

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class ChatSession(Base):
    __tablename__ = "chat_sessions"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, default="New Chat")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")

class ChatMessage(Base):
    __tablename__ = "chat_messages"
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("chat_sessions.id"), nullable=False)
    role = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    session = relationship("ChatSession", back_populates="messages")

def init_db():
    Base.metadata.create_all(bind=engine)

def delete_session(session_id: int):
    """Deletes a chat session and all its associated messages."""
    db = SessionLocal()
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if session:
        db.delete(session)
        db.commit()
    db.close()

def rename_session(session_id: int, new_title: str):
    """Updates the title of a specific chat session."""
    db = SessionLocal()
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if session:
        session.title = new_title
        db.commit()
    db.close()

def export_session_to_markdown(session_id: int) -> str:
    """Converts a chat session's messages into a formatted Markdown string."""
    db = SessionLocal()
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not session:
        db.close()
        return ""

    md_content = f"# Chat Session: {session.title}\n"
    md_content += f"*Exported on: {datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}*\n\n---\n\n"

    for msg in session.messages:
        role_header = "### 👤 User" if msg.role == "user" else "### ⚡ Antigravity Agent"
        timestamp_str = msg.timestamp.strftime('%Y-%m-%d %H:%M')
        md_content += f"{role_header} *({timestamp_str})*\n\n{msg.content}\n\n---\n\n"

    db.close()
    return md_content