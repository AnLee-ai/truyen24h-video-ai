import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Base directories
BASE_DIR = Path(__file__).resolve().parent.parent
SRC_DIR = BASE_DIR / "src"
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "output"
BGM_DIR = BASE_DIR / "bgm"

# Create necessary directories
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
BGM_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)

def _clean_env(var_name: str) -> str:
    val = os.getenv(var_name, "")
    if not val:
        return ""
    return val.strip().strip("'").strip('"').replace('\r', '').replace('\n', '')

# Environment variables
GEMINI_API_KEY = _clean_env("GEMINI_API_KEY")
GROQ_API_KEY = _clean_env("GROQ_API_KEY")
SUPABASE_URL = _clean_env("SUPABASE_URL")
SUPABASE_KEY = _clean_env("SUPABASE_KEY")
TELEGRAM_BOT_TOKEN = _clean_env("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = _clean_env("TELEGRAM_CHAT_ID")

# Model configurations
# Using gemini-flash-latest as the primary fast and free model
GEMINI_MODEL_WRITER = "gemini-2.0-flash"  # Enforce stable 2.0 model to prevent 404 and 20 reqs limit
GEMINI_MODEL_EMBED = os.getenv("GEMINI_MODEL_EMBED", "text-embedding-004")
GROQ_MODEL_WRITER = os.getenv("GROQ_MODEL_WRITER", "llama-3.3-70b-versatile")

# TTS configurations
DEFAULT_VOICE = os.getenv("DEFAULT_VOICE", "vi-VN-HoaiMyNeural")  # Alternative: vi-VN-NamMinhNeural
DEFAULT_RATE = os.getenv("DEFAULT_RATE", "+10%")  # Slightly faster (1.1x) for user preference
DEFAULT_PITCH = os.getenv("DEFAULT_PITCH", "+0Hz")

# Validate critical configs
def validate_config():
    missing = []
    if not GEMINI_API_KEY:
        missing.append("GEMINI_API_KEY")
    if not SUPABASE_URL:
        missing.append("SUPABASE_URL")
    if not SUPABASE_KEY:
        missing.append("SUPABASE_KEY")
    if not TELEGRAM_BOT_TOKEN:
        missing.append("TELEGRAM_BOT_TOKEN")
    if not TELEGRAM_CHAT_ID:
        missing.append("TELEGRAM_CHAT_ID")
    
    if missing:
        print(f"[WARNING] Missing environment variables: {', '.join(missing)}")
        print("Please configure them in your .env file.")
        return False
    return True
