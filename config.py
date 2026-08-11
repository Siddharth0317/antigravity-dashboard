import os
from dotenv import load_dotenv

# Load environment variables from .env file (re-read if updated)
load_dotenv(override=True)

# Fetch sensitive configuration strictly from environment variables
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or os.getenv("API_KEY")
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./shared_data/chat_history.db")

# Create folder for SQLite storage if it doesn't exist
os.makedirs("shared_data", exist_ok=True)