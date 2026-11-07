import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from config.settings import CONTENT_DIR, load_track_config
from core.db import execute_query, execute_write

PASS_THRESHOLD = 80.0
MAX_ATTEMPTS = 3

def get_module_status(learner_id: str, module_id: str, db_path: Optional[Path] = None) -> Dict[str, Any]:
    """Retrieves current progress and status for a module."""
    sql = "SELECT * FROM module_progress WHERE learner_id = ? AND module_id = ?"
    rows = execute_query(sql, (learner_id, module_id), db_path=db_path)
    if rows:
        return dict(rows[0])
    
    # Default if record doesn't exist yet
    return {
        "learner_id": learner_id,
        "module_id": module_id,
        "phase_id": "phase_1",
        "status": "locked",
        "mastery_score": 0.0,
        "mastery_attempts": 0,
        "project_score": 0.0,
        "project_status": "pending",
        "lab_status": "pending",
        "started_at": None,
        "completed_at": None,
        "last_reset_at": None
    }

def record_mastery_attempt(
    learner_id: str,
    module_id: str,
    score: float,
    answers: Dict[str, Any],
    executive_explanation: str,
    code_reading_answer: str,
    weak_concepts: List[str],
    db_path: Optional[Path] = None
) -> Dict[str, Any]:
    """
    Records a mastery check attempt.
    Enforces the 80% pass threshold and max 3 attempts rule.
    """
    now = datetime.now().isoformat()
    passed = 1 if score >= PASS_THRESHOLD else 0
    
    # Get current attempts count
    status = get_module_status(learner_id, module_id, db_path=db_path)
    attempt_num = status.get("mastery_attempts", 0) + 1
    
    # Record the attempt
    sql_attempt = """
    INSERT INTO mastery_attempts (learner_id, module_id, attempt_number, score, passed, answers, executive_explanation, code_reading_answer, weak_concepts, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    execute_write(sql_attempt, (
        learner_id, module_id, attempt_num, score, passed,
        json.dumps(answers), executive_explanation, code_reading_answer,
        json.dumps(weak_concepts), now
    ), db_path=db_path)
    
    # Update module progress
    new_status = status.get("status", "in_progress")
    project_score = status.get("project_score", 0.0)
    lab_passed = (status.get("lab_status") == "passed")
    
    # Fully passed only if mastery check >= 80% AND project passed (>=80%) AND lab passed
    if passed and project_score >= PASS_THRESHOLD and lab_passed:
        new_status = "passed"
        completed_at = now
    elif not passed and attempt_num >= MAX_ATTEMPTS:
        new_status = "needs_review"
        completed_at = None
    else:
        completed_at = None
        
    # Upsert module progress to guarantee row exists
    sql_upsert = """
    INSERT INTO module_progress (learner_id, module_id, phase_id, status, mastery_score, mastery_attempts, project_score, lab_status, started_at, completed_at)
    VALUES (?, ?, 'phase_1', ?, ?, ?, 0.0, 'pending', ?, ?)
    ON CONFLICT(learner_id, module_id) DO UPDATE SET
        mastery_score = excluded.mastery_score,
        mastery_attempts = excluded.mastery_attempts,
        status = excluded.status,
        completed_at = COALESCE(excluded.completed_at, module_progress.completed_at)
    """
    execute_write(sql_upsert, (
        learner_id, module_id, new_status, score, attempt_num, now, completed_at
    ), db_path=db_path)
    
    # If passed, unlock next module
    if new_status == "passed":
        unlock_next_module(learner_id, module_id, db_path=db_path)
        
    return {
        "score": score,
        "passed": bool(passed),
        "attempt_number": attempt_num,
        "max_attempts_reached": (attempt_num >= MAX_ATTEMPTS and not passed),
        "module_status": new_status,
        "weak_concepts": weak_concepts
    }

def unlock_next_module(learner_id: str, completed_module_id: str, db_path: Optional[Path] = None) -> Optional[str]:
    """Unlocks the subsequent module in sequence once a module passes."""
    track = load_track_config()
    all_modules = []
    for phase in track.get("phases", []):
        for mod in phase.get("modules", []):
            all_modules.append(mod["id"])
            
    if completed_module_id in all_modules:
        idx = all_modules.index(completed_module_id)
        if idx + 1 < len(all_modules):
            next_mod = all_modules[idx + 1]
            # Check current status of next module
            curr = get_module_status(learner_id, next_mod, db_path=db_path)
            if curr.get("status") == "locked":
                now = datetime.now().isoformat()
                sql = """
                INSERT INTO module_progress (learner_id, module_id, phase_id, status, started_at)
                VALUES (?, ?, 'phase_1', 'in_progress', ?)
                ON CONFLICT(learner_id, module_id) DO UPDATE SET
                    status = 'in_progress',
                    started_at = excluded.started_at
                """
                execute_write(sql, (learner_id, next_mod, now), db_path=db_path)
                return next_mod
    return None

def reset_module(learner_id: str, module_id: str, force: bool = False, db_path: Optional[Path] = None) -> bool:
    """
    Resets a module's progress so the learner can re-take it.
    Can only be triggered if 3 failed attempts occurred (or admin force).
    """
    status = get_module_status(learner_id, module_id, db_path=db_path)
    if not force and status.get("mastery_attempts", 0) < MAX_ATTEMPTS and status.get("status") != "needs_review":
        return False
        
    now = datetime.now().isoformat()
    sql = """
    UPDATE module_progress
    SET status = 'in_progress',
        mastery_score = 0.0,
        mastery_attempts = 0,
        last_reset_at = ?
    WHERE learner_id = ? AND module_id = ?
    """
    execute_write(sql, (now, learner_id, module_id), db_path=db_path)
    return True

def can_access_module(learner_id: str, module_id: str, db_path: Optional[Path] = None) -> bool:
    """Determines whether learner can access lessons/labs of a module."""
    status = get_module_status(learner_id, module_id, db_path=db_path)
    return status.get("status") in ["in_progress", "passed", "tested_out", "needs_review"]
