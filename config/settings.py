import os
import sys
from pathlib import Path
import yaml
from dotenv import load_dotenv

# Base paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
CONFIG_DIR = PROJECT_ROOT / "config"
TRACKS_DIR = CONFIG_DIR / "tracks"
CONTENT_DIR = PROJECT_ROOT / "content"
SUBMISSIONS_DIR = PROJECT_ROOT / "submissions"
DB_DIR = PROJECT_ROOT / "db"
DEFAULT_DB_PATH = DB_DIR / "aileaderlearn.db"

# Load environment variables
load_dotenv(PROJECT_ROOT / ".env")

# Settings
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "Flound3r2766@00")
SECRET_ENCRYPTION_KEY = os.getenv("SECRET_ENCRYPTION_KEY", "")
DB_PATH = Path(os.getenv("DB_PATH", str(DEFAULT_DB_PATH)))
if not DB_PATH.is_absolute():
    DB_PATH = PROJECT_ROOT / DB_PATH

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# Email SMTP Settings (for password recovery dispatch)
SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM_EMAIL = os.getenv("SMTP_FROM_EMAIL", "noreply@aileaderlearn.com")

# Google Drive / Google Sheets Integration
GOOGLE_SHEET_WEBHOOK_URL = os.getenv("GOOGLE_SHEET_WEBHOOK_URL", "")

def load_track_config(track_id: str = "data_ai_leadership") -> dict:
    track_path = TRACKS_DIR / f"{track_id}.yaml"
    if not track_path.exists():
        # Fallback to default
        track_path = TRACKS_DIR / "data_ai_leadership.yaml"
    with open(track_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)
