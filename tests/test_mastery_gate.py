import pytest
import tempfile
from pathlib import Path
from core.db import init_db, create_learner, execute_query
from core.mastery_gate import (
    record_mastery_attempt, get_module_status, unlock_next_module, reset_module,
    PASS_THRESHOLD, MAX_ATTEMPTS
)

@pytest.fixture
def temp_db():
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_path = Path(tmp_dir) / "test.db"
        init_db(db_path)
        create_learner(
            learner_id="test_learner",
            name="Test Learner",
            track_id="data_ai_leadership",
            current_role="Reporting Lead",
            years_of_experience=6,
            target_level="Head of Analytics",
            industry="Finance",
            tools_known=["Excel"],
            hours_per_week=10,
            start_date="2025-01-01",
            db_path=db_path
        )
        yield db_path

def test_mastery_gate_threshold(temp_db):
    # Score 75% -> Below threshold (should fail)
    rec1 = record_mastery_attempt(
        learner_id="test_learner",
        module_id="module_1",
        score=75.0,
        answers={},
        executive_explanation="test explanation",
        code_reading_answer="test code reading",
        weak_concepts=["OLTP vs OLAP"],
        db_path=temp_db
    )
    assert rec1["passed"] is False
    assert rec1["score"] == 75.0
    assert rec1["attempt_number"] == 1
    
    status = get_module_status("test_learner", "module_1", db_path=temp_db)
    assert status["status"] != "passed"

def test_mastery_pass_and_unlock(temp_db):
    # Set lab and project as passed first via upsert
    from core.db import execute_write
    execute_write(
        "INSERT INTO module_progress (learner_id, module_id, phase_id, status, lab_status, project_score) "
        "VALUES ('test_learner', 'module_1', 'phase_1', 'in_progress', 'passed', 85.0) "
        "ON CONFLICT(learner_id, module_id) DO UPDATE SET lab_status = 'passed', project_score = 85.0",
        db_path=temp_db
    )
    
    # Score 85% -> Passes mastery gate
    rec = record_mastery_attempt(
        learner_id="test_learner",
        module_id="module_1",
        score=85.0,
        answers={},
        executive_explanation="Full sound executive defense.",
        code_reading_answer="Correct prediction.",
        weak_concepts=[],
        db_path=temp_db
    )
    assert rec["passed"] is True
    
    status = get_module_status("test_learner", "module_1", db_path=temp_db)
    assert status["status"] == "passed"
    
    # Check that module 2 was unlocked
    status_m2 = get_module_status("test_learner", "module_2", db_path=temp_db)
    assert status_m2["status"] == "in_progress"

def test_three_attempt_limit_and_reset(temp_db):
    # Fail 3 times
    for i in range(MAX_ATTEMPTS):
        rec = record_mastery_attempt(
            learner_id="test_learner",
            module_id="module_1",
            score=60.0,
            answers={},
            executive_explanation="",
            code_reading_answer="",
            weak_concepts=["Concept A"],
            db_path=temp_db
        )
    
    status = get_module_status("test_learner", "module_1", db_path=temp_db)
    assert status["mastery_attempts"] == 3
    assert status["status"] == "needs_review"
    
    # Can reset
    reset_ok = reset_module("test_learner", "module_1", force=False, db_path=temp_db)
    assert reset_ok is True
    
    status_after = get_module_status("test_learner", "module_1", db_path=temp_db)
    assert status_after["mastery_attempts"] == 0
    assert status_after["status"] == "in_progress"
