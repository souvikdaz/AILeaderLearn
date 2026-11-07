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
    db_path: Optional[Path] = None
) -> Dict[str, Any]:
    from datetime import datetime
    created_at = datetime.now().isoformat()
    tools_json = json.dumps(tools_known)
    sql = """
    INSERT INTO learners (id, name, track_id, current_role, years_of_experience, 
                          target_level, industry, tools_known, hours_per_week, start_date, created_at, status)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'active')
    """
    execute_write(sql, (
        learner_id, name, track_id, current_role, years_of_experience,
        target_level, industry, tools_json, hours_per_week, start_date, created_at
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
