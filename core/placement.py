import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import yaml
from config.settings import CONTENT_DIR
from core.db import execute_query, execute_write

DIAGNOSTIC_PATH = CONTENT_DIR / "diagnostic" / "placement_questions.yaml"

def load_diagnostic_questions() -> List[Dict[str, Any]]:
    """Loads all placement questions from YAML."""
    if not DIAGNOSTIC_PATH.exists():
        return []
    with open(DIAGNOSTIC_PATH, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data.get("questions", [])

def score_placement_answers(
    answers: Dict[str, int], 
    questions: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Scores diagnostic answers.
    answers: dict mapping question_id -> selected_option_index
    Returns structured scoring breakdown, starting module, and test-out recommendations.
    """
    if questions is None:
        questions = load_diagnostic_questions()
        
    q_map = {q["id"]: q for q in questions}
    category_counts = {}
    category_correct = {}
    total_correct = 0
    total_questions = len(questions)
    
    detailed_results = []
    
    for q in questions:
        qid = q["id"]
        cat = q.get("category", "general")
        category_counts[cat] = category_counts.get(cat, 0) + 1
        
        selected = answers.get(qid)
        correct_idx = q.get("correct_index")
        is_correct = (selected == correct_idx)
        
        if is_correct:
            category_correct[cat] = category_correct.get(cat, 0) + 1
            total_correct += 1
            
        detailed_results.append({
            "id": qid,
            "category": cat,
            "is_code_reading": q.get("is_code_reading", False),
            "selected": selected,
            "correct_index": correct_idx,
            "is_correct": is_correct,
            "explanation": q.get("explanation", "")
        })
        
    category_scores = {}
    for cat, total in category_counts.items():
        corr = category_correct.get(cat, 0)
        category_scores[cat] = {
            "correct": corr,
            "total": total,
            "pct": round((corr / total) * 100, 1) if total > 0 else 0.0
        }
        
    total_pct = round((total_correct / total_questions) * 100, 1) if total_questions > 0 else 0.0
    
    # Test-out logic:
    # Learner can test out of Module 1 (Data Flow) if excel_reporting >= 75%
    # Can test out of Module 2 (SQL Reading) if sql_reading >= 80%
    # Can test out of Module 3 (Python) if python_reading >= 80%
    tested_out_modules = []
    
    excel_pct = category_scores.get("excel_reporting", {}).get("pct", 0)
    sql_pct = category_scores.get("sql_reading", {}).get("pct", 0)
    python_pct = category_scores.get("python_reading", {}).get("pct", 0)
    
    if excel_pct >= 75.0:
        tested_out_modules.append("module_1")
    if sql_pct >= 80.0:
        tested_out_modules.append("module_2")
    if python_pct >= 80.0:
        tested_out_modules.append("module_3")
        
    # Starting module is the first module not tested out
    all_p1_modules = ["module_1", "module_2", "module_3", "module_4"]
    starting_module = "module_1"
    for mod in all_p1_modules:
        if mod not in tested_out_modules:
            starting_module = mod
            break
    else:
        starting_module = "module_5" # Advanced directly to Phase 2
        
    return {
        "total_score": total_pct,
        "total_correct": total_correct,
        "total_questions": total_questions,
        "category_scores": category_scores,
        "tested_out_modules": tested_out_modules,
        "starting_module": starting_module,
        "details": detailed_results
    }

def record_diagnostic_result(
    learner_id: str,
    answers: Dict[str, int],
    db_path: Optional[Path] = None
) -> Dict[str, Any]:
    """Scores diagnostic, records in DB, updates module progress, and initializes track modules."""
    from datetime import datetime
    
    result = score_placement_answers(answers)
    now = datetime.now().isoformat()
    
    # Save diagnostic result
    sql = """
    INSERT INTO diagnostic_results (learner_id, total_score, category_scores, starting_module, tested_out_modules, answers, completed_at)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """
    execute_write(sql, (
        learner_id,
        result["total_score"],
        json.dumps(result["category_scores"]),
        result["starting_module"],
        json.dumps(result["tested_out_modules"]),
        json.dumps(answers),
        now
    ), db_path=db_path)
    
    # Initialize module progress for all Phase 1-4 modules
    from config.settings import load_track_config
    track = load_track_config()
    
    for phase in track.get("phases", []):
        phase_id = phase["id"]
        for mod in phase.get("modules", []):
            mod_id = mod["id"]
            
            # Determine initial status
            if mod_id in result["tested_out_modules"]:
                status = "tested_out"
                mastery_score = 85.0
            elif mod_id == result["starting_module"]:
                status = "in_progress"
                mastery_score = 0.0
            else:
                status = "locked"
                mastery_score = 0.0
                
            mod_sql = """
            INSERT INTO module_progress (learner_id, module_id, phase_id, status, mastery_score, mastery_attempts, project_score, project_status, started_at)
            VALUES (?, ?, ?, ?, ?, 0, 0.0, 'pending', ?)
            ON CONFLICT(learner_id, module_id) DO UPDATE SET
                status = excluded.status,
                mastery_score = excluded.mastery_score,
                started_at = excluded.started_at
            """
            execute_write(mod_sql, (
                learner_id, mod_id, phase_id, status, mastery_score,
                now if status == "in_progress" else None
            ), db_path=db_path)
            
    return result

def get_learner_diagnostic(learner_id: str, db_path: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    """Retrieves learner's latest diagnostic result."""
    sql = "SELECT * FROM diagnostic_results WHERE learner_id = ? ORDER BY completed_at DESC LIMIT 1"
    rows = execute_query(sql, (learner_id,), db_path=db_path)
    if not rows:
        return None
    r = dict(rows[0])
    r["category_scores"] = json.loads(r["category_scores"])
    r["tested_out_modules"] = json.loads(r["tested_out_modules"])
    if r.get("answers"):
        r["answers"] = json.loads(r["answers"])
    return r
