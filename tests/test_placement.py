import pytest
import tempfile
from pathlib import Path
from core.db import init_db, create_learner
from core.placement import (
    load_diagnostic_questions, score_placement_answers, record_diagnostic_result,
    save_diagnostic_draft, get_diagnostic_draft, delete_diagnostic_draft,
    has_completed_diagnostic
)

def test_load_diagnostic_questions():
    questions = load_diagnostic_questions()
    assert len(questions) >= 20
    # Verify code reading questions exist
    code_reading = [q for q in questions if q.get("is_code_reading")]
    assert len(code_reading) >= 3
    # Verify every question has "I don't know" as an option
    for q in questions:
        assert "options" in q
        assert "I don't know" in q["options"]
        assert q["options"][-1] == "I don't know"

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

def test_diagnostic_draft_lifecycle():
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_path = Path(tmp_dir) / "test.db"
        init_db(db_path)
        create_learner(
            learner_id="draft_user",
            name="Draft User",
            track_id="data_ai_leadership",
            current_role="Analyst",
            years_of_experience=4,
            target_level="Head of Analytics",
            industry="Finance",
            tools_known=["Excel"],
            hours_per_week=10,
            start_date="2026-11-01",
            db_path=db_path
        )
        
        # 1. Initially uncompleted, no draft
        assert has_completed_diagnostic("draft_user", db_path=db_path) is False
        assert get_diagnostic_draft("draft_user", db_path=db_path) == {}
        
        # 2. Save partial draft (3 questions answered, 1 None)
        partial = {"q1": 0, "q2": 2, "q3": 1, "q4": None}
        save_diagnostic_draft("draft_user", partial, db_path=db_path)
        
        saved = get_diagnostic_draft("draft_user", db_path=db_path)
        assert len(saved) == 3
        assert saved["q1"] == 0
        assert saved["q2"] == 2
        assert saved["q3"] == 1
        assert "q4" not in saved
        assert has_completed_diagnostic("draft_user", db_path=db_path) is False
        
        # 3. Update draft with more answers
        partial["q4"] = 3
        partial["q5"] = 0
        save_diagnostic_draft("draft_user", partial, db_path=db_path)
        saved_updated = get_diagnostic_draft("draft_user", db_path=db_path)
        assert len(saved_updated) == 5
        assert saved_updated["q4"] == 3
        assert saved_updated["q5"] == 0
        
        # 4. Record full diagnostic completion
        questions = load_diagnostic_questions()
        full_answers = {q["id"]: q["correct_index"] for q in questions}
        record_diagnostic_result("draft_user", full_answers, db_path=db_path)
        
        # 5. Diagnostic is completed, draft is purged
        assert has_completed_diagnostic("draft_user", db_path=db_path) is True
        assert get_diagnostic_draft("draft_user", db_path=db_path) == {}

def test_diagnostic_i_dont_know_option():
    """Verifies that selecting 'I don't know' across questions scores 0 without errors."""
    questions = load_diagnostic_questions()
    
    # 1. Answer "I don't know" for every question
    idk_answers = {}
    for q in questions:
        idk_index = q["options"].index("I don't know")
        idk_answers[q["id"]] = idk_index
        
    result = score_placement_answers(idk_answers, questions)
    assert result["total_score"] == 0.0
    assert result["total_correct"] == 0
    assert result["total_questions"] == len(questions)
    assert result["tested_out_modules"] == []
    assert result["starting_module"] == "module_1"
    
    # Verify details reflect "I don't know" selection
    for detail in result["details"]:
        assert detail["is_correct"] is False
        
    # 2. Mixed: perfect in excel_reporting, but "I don't know" for all others
    mixed_answers = {}
    for q in questions:
        if q["category"] == "excel_reporting":
            mixed_answers[q["id"]] = q["correct_index"]
        else:
            mixed_answers[q["id"]] = q["options"].index("I don't know")
            
    mixed_res = score_placement_answers(mixed_answers, questions)
    assert mixed_res["category_scores"]["excel_reporting"]["pct"] == 100.0
    assert "module_1" in mixed_res["tested_out_modules"]
    assert "module_2" not in mixed_res["tested_out_modules"]
    assert mixed_res["starting_module"] == "module_2"
