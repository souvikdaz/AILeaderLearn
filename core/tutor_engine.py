import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from config.settings import CONTENT_DIR, GEMINI_API_KEY, OPENAI_API_KEY
from core.db import execute_query, execute_write

def load_module_lessons(module_id: str) -> List[Dict[str, Any]]:
    """Loads all lessons for a given module across any phase directory."""
    for phase_dir in CONTENT_DIR.iterdir():
        if phase_dir.is_dir():
            for sub in phase_dir.iterdir():
                if sub.is_dir():
                    yaml_file = sub / "lessons.yaml"
                    if yaml_file.exists():
                        import yaml
                        with open(yaml_file, "r", encoding="utf-8") as f:
                            data = yaml.safe_load(f)
                        if data.get("module_id") == module_id:
                            return data.get("lessons", [])
    return []

def get_lesson_progress(learner_id: str, module_id: str, lesson_id: str, db_path: Optional[Path] = None) -> Dict[str, Any]:
    """Retrieves learner's interactive chat history and completion status for a lesson."""
    sql = "SELECT * FROM lesson_progress WHERE learner_id = ? AND module_id = ? AND lesson_id = ?"
    rows = execute_query(sql, (learner_id, module_id, lesson_id), db_path=db_path)
    if rows:
        r = dict(rows[0])
        r["chat_history"] = json.loads(r["chat_history"] or "[]")
        return r
    return {
        "learner_id": learner_id,
        "module_id": module_id,
        "lesson_id": lesson_id,
        "status": "not_started",
        "chat_history": [],
        "practice_completed": 0,
        "completed_at": None
    }

def log_misconception(
    learner_id: str,
    module_id: str,
    lesson_id: str,
    concept: str,
    error_type: str,
    misconception_name: str,
    context: str = "",
    db_path: Optional[Path] = None
) -> None:
    """Logs a diagnosed misconception to SQLite."""
    now = datetime.now().isoformat()
    sql = """
    INSERT INTO misconceptions (learner_id, module_id, lesson_id, concept, error_type, misconception_name, context, occurred_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """
    execute_write(sql, (learner_id, module_id, lesson_id, concept, error_type, misconception_name, context, now), db_path=db_path)

def evaluate_check_answer(
    learner_id: str,
    module_id: str,
    lesson_id: str,
    question: Dict[str, Any],
    selected_option_index: int,
    db_path: Optional[Path] = None
) -> Dict[str, Any]:
    """
    Evaluates learner's answer to a check question.
    If wrong, names the exact misconception, re-teaches with a concrete new scenario, and logs the incident.
    """
    correct_idx = question.get("correct_index", 0)
    is_correct = (selected_option_index == correct_idx)
    
    if is_correct:
        response_text = f"**Correct!** Excellent technical judgment.\n\n"
        if question.get("explanation"):
            response_text += question["explanation"]
        misconception_diagnosed = None
    else:
        misconception_name = question.get("misconception_name", "Conceptual Misalignment")
        error_type = question.get("error_type", "logic_error")
        re_teach = question.get("re_teach", "Review the underlying data architecture concept.")
        concept = question.get("concept", lesson_id)
        
        # Log to DB immediately
        log_misconception(
            learner_id=learner_id,
            module_id=module_id,
            lesson_id=lesson_id,
            concept=concept,
            error_type=error_type,
            misconception_name=misconception_name,
            context=f"Selected option {selected_option_index} on question '{question.get('prompt', '')[:80]}...'",
            db_path=db_path
        )
        
        response_text = (
            f"**Not quite. Diagnosed Misconception:** *{misconception_name}*\n\n"
            f"**Why this matters for a leader:** {re_teach}\n\n"
            f"**Worked Scenario Re-Teach:** Consider what happens when an executive asks for audited numbers: "
            f"if we apply the flawed logic, the metric shifts without an operational cause, undermining board confidence."
        )
        misconception_diagnosed = misconception_name
        
    return {
        "is_correct": is_correct,
        "response_text": response_text,
        "misconception": misconception_diagnosed
    }

def record_lesson_action(
    learner_id: str,
    module_id: str,
    lesson_id: str,
    action: str, # 'complete', 'skip', 'explain_again', 'more_practice'
    chat_history: List[Dict[str, str]],
    db_path: Optional[Path] = None
) -> None:
    """
    Saves chat messages, status, and completion/skip events to SQLite.
    """
    now = datetime.now().isoformat()
    status = "completed" if action == "complete" else ("skipped" if action == "skip" else "in_progress")
    
    sql = """
    INSERT INTO lesson_progress (learner_id, module_id, lesson_id, status, chat_history, completed_at)
    VALUES (?, ?, ?, ?, ?, ?)
    ON CONFLICT(learner_id, module_id, lesson_id) DO UPDATE SET
        status = excluded.status,
        chat_history = excluded.chat_history,
        completed_at = COALESCE(excluded.completed_at, lesson_progress.completed_at)
    """
    execute_write(sql, (
        learner_id, module_id, lesson_id, status, json.dumps(chat_history),
        now if status in ["completed", "skipped"] else None
    ), db_path=db_path)

def generate_tutor_response(
    user_prompt: str,
    lesson_context: Dict[str, Any],
    chat_history: List[Dict[str, str]]
) -> str:
    """
    Generates intelligent pedagogical tutor responses.
    Uses LLM API if key is present; otherwise falls back to a deterministic, high-signal leadership tutor engine.
    """
    # Check if Gemini API Key is configured
    if GEMINI_API_KEY:
        try:
            import requests
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
            sys_instruction = (
                "You are an elite Data & AI Leadership Tutor. Your student is an experienced MIS/reporting professional "
                "transitioning to Head of Analytics or AI Lead. Explain technical concepts in plain English (<200 words), "
                "connect Excel concepts to modern data pipelines, emphasize executive decision-making, and challenge flawed assumptions."
            )
            contents = [
                {"role": "user", "parts": [{"text": f"Context Lesson: {lesson_context.get('title', '')}\nConcept: {lesson_context.get('concept', '')}\n\nUser Question: {user_prompt}"}]}
            ]
            resp = requests.post(url, json={"systemInstruction": {"parts": [{"text": sys_instruction}]}, "contents": contents}, timeout=6)
            if resp.status_code == 200:
                data = resp.json()
                return data["candidates"][0]["content"]["parts"][0]["text"]
        except Exception:
            pass # Fall through to heuristic tutor
            
    # Deterministic Leadership Heuristic Tutor Engine
    lower = user_prompt.lower()
    
    if "explain again" in lower or "simpler" in lower:
        return (
            f"**Let's simplify with an everyday analogy:**\n\n"
            f"Think of **{lesson_context.get('concept', 'this concept')}** like an automated restaurant kitchen. "
            f"{lesson_context.get('analogy', 'Operations must separate raw ingredient prep from plating for the customer.')}\n\n"
            f"**The Leader's Rule of Thumb:** If this breaks, ask your team: *'{lesson_context.get('leader_questions', {}).get('what_to_ask', 'Where is the governed definition?')}'*"
        )
    elif "more practice" in lower or "exercise" in lower:
        return (
            f"**Scenario Challenge:** Imagine your CEO pings you on Slack at 8:30 PM: *'The board says our retention numbers are down 8% compared to last quarter, but sales says we grew.'*\n\n"
            f"Based on what we just learned about **{lesson_context.get('concept', 'data flow and metrics')}**, what are the first two questions you ask your analytics lead before responding to the CEO?"
        )
    elif "why" in lower or "excel" in lower:
        return (
            f"**Bridging from Excel to Leadership:** In Excel, you have complete control over individual cell formulas. "
            f"In enterprise scale, having 50 people edit their own Excel formulas causes conflicting versions of truth. "
            f"By moving to governed pipelines and semantic layers, you turn fragile personal spreadsheets into a single company-wide asset."
        )
    else:
        return (
            f"**Leadership Perspective on {lesson_context.get('concept', 'this topic')}:**\n\n"
            f"As a technical leader, you don't need to write every line of code yourself—you need to know what questions to ask to verify your team's work.\n\n"
            f"1. **Audit the Grain:** Verify row counts before and after joins.\n"
            f"2. **Check the Boundaries:** Verify how nulls, refunds, and inactive accounts are handled.\n"
            f"3. **Focus on the Decision:** Tie the metric directly to P&L impact."
        )
