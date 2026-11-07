import os
from pathlib import Path
import yaml
from dotenv import load_dotenv

# Base paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = PROJECT_ROOT / "config"
TRACKS_DIR = CONFIG_DIR / "tracks"
CONTENT_DIR = PROJECT_ROOT / "content"
SUBMISSIONS_DIR = PROJECT_ROOT / "submissions"
DB_DIR = PROJECT_ROOT / "db"
DEFAULT_DB_PATH = DB_DIR / "aileaderlearn.db"

# Load environment variables
load_dotenv(PROJECT_ROOT / ".env")

# Settings
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "leader_admin_2025")
DB_PATH = Path(os.getenv("DB_PATH", str(DEFAULT_DB_PATH)))
if not DB_PATH.is_absolute():
    DB_PATH = PROJECT_ROOT / DB_PATH

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

def load_track_config(track_id: str = "data_ai_leadership") -> dict:
    track_path = TRACKS_DIR / f"{track_id}.yaml"
    if not track_path.exists():
        # Fallback to default
        track_path = TRACKS_DIR / "data_ai_leadership.yaml"
    with open(track_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)
