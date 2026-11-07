import pytest
import tempfile
from pathlib import Path
from core.db import init_db, create_learner
from core.placement import (
    load_diagnostic_questions, score_placement_answers, record_diagnostic_result
)

def test_load_diagnostic_questions():
    questions = load_diagnostic_questions()
    assert len(questions) >= 20
    # Verify code reading questions exist
    code_reading = [q for q in questions if q.get("is_code_reading")]
    assert len(code_reading) >= 3

def test_score_placement_answers():
    questions = load_diagnostic_questions()
    # Build 100% correct answers
    perfect_answers = {q["id"]: q["correct_index"] for q in questions}
    
    res = score_placement_answers(perfect_answers, questions)
    assert res["total_score"] == 100.0
    assert len(res["tested_out_modules"]) >= 3
    assert "module_1" in res["tested_out_modules"]
    assert "module_2" in res["tested_out_modules"]
    assert "module_3" in res["tested_out_modules"]

def test_record_diagnostic_result():
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_path = Path(tmp_dir) / "test.db"
        init_db(db_path)
        create_learner(
            learner_id="diag_user",
            name="Diag User",
            track_id="data_ai_leadership",
            current_role="Analyst",
            years_of_experience=4,
            target_level="Head of Analytics",
            industry="Healthcare",
            tools_known=["Excel"],
            hours_per_week=10,
            start_date="2025-01-01",
            db_path=db_path
        )
        
        questions = load_diagnostic_questions()
        # All wrong answers
        wrong_answers = {q["id"]: (q["correct_index"] + 1) % len(q["options"]) for q in questions}
        
        result = record_diagnostic_result("diag_user", wrong_answers, db_path=db_path)
        assert result["total_score"] == 0.0
        assert result["tested_out_modules"] == []
        assert result["starting_module"] == "module_1"
