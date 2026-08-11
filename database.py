import datetime
import hashlib
import secrets
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from config import DATABASE_URL, ADMIN_USERNAME, ADMIN_PASSWORD

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def hash_password(password: str, salt: str = None) -> tuple[str, str]:
    """Generates a secure SHA-256 PBKDF2 password hash with a unique salt."""
    if not salt:
        salt = secrets.token_hex(16)
    pwd_hash = hashlib.pbkdf2_hmac(
        'sha256', 
        password.encode('utf-8'), 
        salt.encode('utf-8'), 
        100000
    ).hex()
    return pwd_hash, salt

def verify_password(password: str, pwd_hash: str, salt: str) -> bool:
    """Verifies password against stored hash using constant-time comparison."""
    calculated_hash, _ = hash_password(password, salt)
    return secrets.compare_digest(calculated_hash, pwd_hash)

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    salt = Column(String, nullable=False)
    role = Column(String, default="user") # "admin" or "user"
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    sessions = relationship("ChatSession", back_populates="user")

class ChatSession(Base):
    __tablename__ = "chat_sessions"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    title = Column(String, default="New Chat")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")
    user = relationship("User", back_populates="sessions")

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
    migrate_db()
    seed_default_users()

def migrate_db():
    """Applies lightweight migrations for SQLite tables."""
    try:
        with engine.connect() as conn:
            result = conn.exec_driver_sql("PRAGMA table_info(chat_sessions)").fetchall()
            columns = [row[1] for row in result]
            if "user_id" not in columns:
                conn.exec_driver_sql("ALTER TABLE chat_sessions ADD COLUMN user_id INTEGER REFERENCES users(id)")
                conn.commit()
    except Exception as e:
        print(f"[Database Migration Warning] {e}")

def seed_default_users():
    """Seeds initial admin account if no users exist in database."""
    db = SessionLocal()
    user_count = db.query(User).count()
    if user_count == 0:
        admin_user = ADMIN_USERNAME or "admin"
        admin_pass = ADMIN_PASSWORD or "admin123"
        pwd_hash, salt = hash_password(admin_pass)
        new_admin = User(username=admin_user, password_hash=pwd_hash, salt=salt, role="admin")
        db.add(new_admin)
        db.commit()
    db.close()

def create_user(username: str, password: str, role: str = "user") -> tuple[bool, str]:
    """Creates a new user account with hashed password."""
    db = SessionLocal()
    existing = db.query(User).filter(User.username == username.strip()).first()
    if existing:
        db.close()
        return False, "Username already exists."
    
    pwd_hash, salt = hash_password(password)
    user = User(username=username.strip(), password_hash=pwd_hash, salt=salt, role=role)
    db.add(user)
    db.commit()
    db.close()
    return True, "User registered successfully!"

def authenticate_user(username: str, password: str):
    """Authenticates user credentials against database."""
    db = SessionLocal()
    user = db.query(User).filter(User.username == username.strip()).first()
    if user and verify_password(password, user.password_hash, user.salt):
        user_info = {"id": user.id, "username": user.username, "role": user.role}
        db.close()
        return user_info
    db.close()
    return None

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