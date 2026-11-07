import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from core.db import execute_query, execute_write

INTERVAL_STEPS = [1, 3, 7, 14]

def schedule_module_concepts_for_review(
    learner_id: str,
    module_id: str,
    concepts: List[Dict[str, str]],
    db_path: Optional[Path] = None
) -> None:
    """
    Schedules passed module concepts into the spaced review queue at Day 1.
    concepts: list of dicts with keys 'concept_id' and optional 'question_id'
    """
    now = datetime.now()
    first_due = (now + timedelta(days=1)).strftime("%Y-%m-%d")
    
    for c in concepts:
        concept_id = c.get("concept_id", "concept_gen")
        qid = c.get("question_id", "")
        
        sql = """
        INSERT INTO quiz_reviews (learner_id, concept_id, module_id, question_id, interval_days, due_date, status, history)
        VALUES (?, ?, ?, ?, 1, ?, 'due', '[]')
        ON CONFLICT(learner_id, concept_id) DO UPDATE SET
            due_date = excluded.due_date,
            status = 'due'
        """
        execute_write(sql, (learner_id, concept_id, module_id, qid, first_due), db_path=db_path)

def get_review_queue(learner_id: str, db_path: Optional[Path] = None) -> Dict[str, Any]:
    """
    Retrieves the spaced repetition review queue partitioned into:
    - Overdue items
    - Due today items
    - Upcoming items
    """
    today_str = datetime.now().strftime("%Y-%m-%d")
    
    sql = """
    SELECT * FROM quiz_reviews 
    WHERE learner_id = ? AND status != 'mastered'
    ORDER BY due_date ASC
    """
    rows = execute_query(sql, (learner_id,), db_path=db_path)
    
    overdue = []
    due_today = []
    upcoming = []
    
    for r in rows:
        item = dict(r)
        if item.get("history"):
            try:
                item["history"] = json.loads(item["history"])
            except Exception:
                item["history"] = []
                
        due_date = item.get("due_date", today_str)
        if due_date < today_str:
            overdue.append(item)
        elif due_date == today_str:
            due_today.append(item)
        else:
            upcoming.append(item)
            
    return {
        "overdue": overdue,
        "due_today": due_today,
        "upcoming": upcoming,
        "total_active_queue": len(overdue) + len(due_today),
        "total_overdue_count": len(overdue),
        "total_due_today_count": len(due_today)
    }

def record_review_result(
    review_id: int,
    score: float,
    passed: bool,
    db_path: Optional[Path] = None
) -> Dict[str, Any]:
    """
    Updates the review item interval based on spaced repetition rules:
    - If passed (>=80%): advances to next interval in [1, 3, 7, 14]. If already at 14, marked 'mastered'.
    - If failed: resets interval to 1 day, sets status to 'due', and marks concept for reteaching.
    """
    sql_get = "SELECT * FROM quiz_reviews WHERE id = ?"
    rows = execute_query(sql_get, (review_id,), db_path=db_path)
    if not rows:
        return {"success": False, "error": "Review item not found"}
        
    curr = dict(rows[0])
    current_interval = curr.get("interval_days", 1)
    history = json.loads(curr.get("history") or "[]")
    
    now = datetime.now()
    today_str = now.strftime("%Y-%m-%d")
    
    history.append({
        "timestamp": now.isoformat(),
        "score": score,
        "passed": passed,
        "previous_interval": current_interval
    })
    
    if passed and score >= 80.0:
        if current_interval == 1:
            next_interval = 3
        elif current_interval == 3:
            next_interval = 7
        elif current_interval == 7:
            next_interval = 14
        else:
            # Reached end of 14-day cycle!
            next_interval = 14
            status = "mastered"
            new_due = today_str
            sql_update = """
            UPDATE quiz_reviews
            SET last_reviewed_at = ?,
                last_score = ?,
                status = 'mastered',
                history = ?
            WHERE id = ?
            """
            execute_write(sql_update, (now.isoformat(), score, json.dumps(history), review_id), db_path=db_path)
            return {
                "success": True,
                "status": "mastered",
                "next_interval": next_interval,
                "due_date": new_due
            }
            
        status = "pending"
        new_due = (now + timedelta(days=next_interval)).strftime("%Y-%m-%d")
    else:
        # Failed review: reset interval back to 1 day
        next_interval = 1
        status = "due"
        new_due = (now + timedelta(days=1)).strftime("%Y-%m-%d")
        
    sql_update = """
    UPDATE quiz_reviews
    SET interval_days = ?,
        due_date = ?,
        last_reviewed_at = ?,
        last_score = ?,
        status = ?,
        history = ?
    WHERE id = ?
    """
    execute_write(sql_update, (
        next_interval, new_due, now.isoformat(), score, status, json.dumps(history), review_id
    ), db_path=db_path)
    
    return {
        "success": True,
        "status": status,
        "next_interval": next_interval,
        "due_date": new_due
    }
