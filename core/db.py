import sqlite3
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from config.settings import DB_PATH, PROJECT_ROOT

SCHEMA_PATH = PROJECT_ROOT / "db" / "schema.sql"

def get_db_connection(db_path: Optional[Path] = None) -> sqlite3.Connection:
    """Returns a SQLite connection with row factory enabled."""
    target_path = Path(db_path) if db_path else DB_PATH
    target_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(target_path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    # Enable foreign keys and WAL mode for better concurrency
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    return conn

def init_db(db_path: Optional[Path] = None) -> None:
    """Initializes the database schema if tables do not exist."""
    conn = get_db_connection(db_path)
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        schema_sql = f.read()
    conn.executescript(schema_sql)
    
    # Ensure necessary columns exist in learners
    cursor = conn.cursor()
    cols = [c[1] for c in cursor.execute("PRAGMA table_info(learners)").fetchall()]
    if "last_active_at" not in cols:
        cursor.execute("ALTER TABLE learners ADD COLUMN last_active_at TEXT;")
    if "email" not in cols:
        cursor.execute("ALTER TABLE learners ADD COLUMN email TEXT;")
    if "password_hash" not in cols:
        cursor.execute("ALTER TABLE learners ADD COLUMN password_hash TEXT;")
        
    conn.commit()
    conn.close()

# Database Helper Functions

def execute_query(sql: str, params: Tuple = (), db_path: Optional[Path] = None) -> List[sqlite3.Row]:
    """Executes a read query and returns rows."""
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        return rows
    finally:
        conn.close()

def execute_write(sql: str, params: Tuple = (), db_path: Optional[Path] = None) -> int:
    """Executes an insert/update/delete query and commits immediately. Returns lastrowid or rowcount."""
    conn = get_db_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute(sql, params)
        conn.commit()
        return cursor.lastrowid if cursor.lastrowid else cursor.rowcount
    finally:
        conn.close()

def execute_script(sql: str, db_path: Optional[Path] = None) -> None:
    """Executes a multi-statement script."""
    conn = get_db_connection(db_path)
    try:
        conn.executescript(sql)
        conn.commit()
    finally:
        conn.close()

# Learner Operations

def get_all_learners(db_path: Optional[Path] = None) -> List[Dict[str, Any]]:
    rows = execute_query("SELECT * FROM learners ORDER BY created_at DESC", db_path=db_path)
    return [dict(r) for r in rows]

def get_learner(learner_id: str, db_path: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    rows = execute_query("SELECT * FROM learners WHERE id = ?", (learner_id,), db_path=db_path)
    return dict(rows[0]) if rows else None

def get_learner_by_email(email: str, db_path: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    """Retrieves a learner by email address (case-insensitive)."""
    if not email:
        return None
    rows = execute_query("SELECT * FROM learners WHERE LOWER(email) = LOWER(?)", (email.strip(),), db_path=db_path)
    return dict(rows[0]) if rows else None

def create_learner(
    learner_id: str,
    name: str,
    track_id: str,
    current_role: str,
    years_of_experience: int,
    target_level: str,
    industry: str,
    tools_known: List[str],
    hours_per_week: int,
    start_date: str,
    email: str = "",
    password_hash: str = "",
    db_path: Optional[Path] = None
) -> Dict[str, Any]:
    from datetime import datetime
    created_at = datetime.now().isoformat()
    tools_json = json.dumps(tools_known)
    sql = """
    INSERT INTO learners (id, name, track_id, current_role, years_of_experience, 
                          target_level, industry, tools_known, hours_per_week, start_date, 
                          created_at, last_active_at, email, password_hash, status)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'active')
    """
    execute_write(sql, (
        learner_id, name, track_id, current_role, years_of_experience,
        target_level, industry, tools_json, hours_per_week, start_date, 
        created_at, created_at, email.strip(), password_hash.strip()
    ), db_path=db_path)
    return get_learner(learner_id, db_path=db_path) # type: ignore

def update_learner(learner_id: str, updates: Dict[str, Any], db_path: Optional[Path] = None) -> None:
    if not updates:
        return
    fields = []
    values = []
    for k, v in updates.items():
        fields.append(f"{k} = ?")
        if isinstance(v, (list, dict)):
            values.append(json.dumps(v))
        else:
            values.append(v)
    values.append(learner_id)
    sql = f"UPDATE learners SET {', '.join(fields)} WHERE id = ?"
    execute_write(sql, tuple(values), db_path=db_path)

def record_learner_activity(learner_id: str, timestamp: Optional[str] = None, db_path: Optional[Path] = None) -> None:
    """Updates the learner's last active timestamp."""
    from datetime import datetime
    act_time = timestamp or datetime.now().isoformat()
    execute_write(
        "UPDATE learners SET last_active_at = ? WHERE id = ?",
        (act_time, learner_id),
        db_path=db_path
    )

def get_learner_last_active(learner_id: str, db_path: Optional[Path] = None) -> str:
    """Discovers and returns the most recent activity timestamp for a learner."""
    rows = execute_query("SELECT last_active_at, created_at FROM learners WHERE id = ?", (learner_id,), db_path=db_path)
    if not rows:
        return "Unknown"
    
    learner = dict(rows[0])
    if learner.get("last_active_at"):
        raw = str(learner["last_active_at"])
        return raw[:19].replace("T", " ")
        
    # Check max activity across all telemetry tables
    q = """
    SELECT MAX(act_time) FROM (
        SELECT MAX(created_at) AS act_time FROM lab_attempts WHERE learner_id = ?
        UNION ALL
        SELECT MAX(submitted_at) AS act_time FROM submissions WHERE learner_id = ?
        UNION ALL
        SELECT MAX(created_at) AS act_time FROM mastery_attempts WHERE learner_id = ?
        UNION ALL
        SELECT MAX(completed_at) AS act_time FROM diagnostic_results WHERE learner_id = ?
        UNION ALL
        SELECT MAX(completed_at) AS act_time FROM lesson_progress WHERE learner_id = ?
        UNION ALL
        SELECT MAX(created_at) AS act_time FROM interview_attempts WHERE learner_id = ?
        UNION ALL
        SELECT MAX(last_reviewed_at) AS act_time FROM quiz_reviews WHERE learner_id = ?
        UNION ALL
        SELECT created_at AS act_time FROM learners WHERE id = ?
    )
    """
    res = execute_query(q, (learner_id, learner_id, learner_id, learner_id, learner_id, learner_id, learner_id, learner_id), db_path=db_path)
    if res and res[0][0]:
        found_time = str(res[0][0])
        execute_write("UPDATE learners SET last_active_at = ? WHERE id = ?", (found_time, learner_id), db_path=db_path)
        return found_time[:19].replace("T", " ")
        
    created = learner.get("created_at", "Never")
    return str(created)[:19].replace("T", " ") if created != "Never" else "Never"

def get_all_learners_with_activity(db_path: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Returns all learners with populated last active date and progress summary."""
    learners = get_all_learners(db_path=db_path)
    enriched = []
    for l in learners:
        d = dict(l)
        d["last_active_date"] = get_learner_last_active(l["id"], db_path=db_path)
        passed = execute_query(
            "SELECT COUNT(*) AS c FROM module_progress WHERE learner_id = ? AND status IN ('passed', 'tested_out')",
            (l["id"],),
            db_path=db_path
        )
        d["passed_modules"] = passed[0]["c"] if passed else 0
        enriched.append(d)
    return enriched

def delete_learner(learner_id: str, db_path: Optional[Path] = None) -> bool:
    """Permanently deletes a learner profile and purges all related tables and file submissions."""
    import shutil
    from config.settings import PROJECT_ROOT
    
    # 1. Cascade delete all dependent relational records
    tables = [
        "interview_attempts",
        "mastery_attempts",
        "submissions",
        "lab_attempts",
        "misconceptions",
        "quiz_reviews",
        "lesson_progress",
        "module_progress",
        "diagnostic_results",
        "learners"
    ]
    for tbl in tables:
        col = "id" if tbl == "learners" else "learner_id"
        execute_write(f"DELETE FROM {tbl} WHERE {col} = ?", (learner_id,), db_path=db_path)
        
    # 2. Clean up file submissions on disk
    sub_dir = PROJECT_ROOT / "submissions" / learner_id
    if sub_dir.exists():
        shutil.rmtree(sub_dir, ignore_errors=True)
        
    return True
