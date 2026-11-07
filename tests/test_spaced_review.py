import pytest
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from core.db import init_db, create_learner, execute_query
from core.review_scheduler import (
    schedule_module_concepts_for_review, get_review_queue, record_review_result
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
            current_role="Manager",
            years_of_experience=5,
            target_level="Head of Analytics",
            industry="Tech",
            tools_known=["Excel"],
            hours_per_week=10,
            start_date="2025-01-01",
            db_path=db_path
        )
        yield db_path

def test_spaced_review_queue_scheduling(temp_db):
    concepts = [
        {"concept_id": "concept_1", "question_id": "q1"},
        {"concept_id": "concept_2", "question_id": "q2"}
    ]
    schedule_module_concepts_for_review("test_learner", "module_1", concepts, db_path=temp_db)
    
    rows = execute_query("SELECT * FROM quiz_reviews WHERE learner_id = 'test_learner'", db_path=temp_db)
    assert len(rows) == 2
    assert rows[0]["interval_days"] == 1

def test_spaced_review_interval_advancement(temp_db):
    concepts = [{"concept_id": "concept_advance", "question_id": "q_adv"}]
    schedule_module_concepts_for_review("test_learner", "module_1", concepts, db_path=temp_db)
    
    rows = execute_query("SELECT id FROM quiz_reviews WHERE concept_id = 'concept_advance'", db_path=temp_db)
    rev_id = rows[0]["id"]
    
    # Pass 1: 1 -> 3
    res1 = record_review_result(rev_id, score=90.0, passed=True, db_path=temp_db)
    assert res1["next_interval"] == 3
    assert res1["status"] == "pending"
    
    # Pass 2: 3 -> 7
    res2 = record_review_result(rev_id, score=85.0, passed=True, db_path=temp_db)
    assert res2["next_interval"] == 7
    
    # Pass 3: 7 -> 14
    res3 = record_review_result(rev_id, score=95.0, passed=True, db_path=temp_db)
    assert res3["next_interval"] == 14
    
    # Pass 4: 14 -> Mastered!
    res4 = record_review_result(rev_id, score=100.0, passed=True, db_path=temp_db)
    assert res4["status"] == "mastered"

def test_spaced_review_failure_resets_interval(temp_db):
    concepts = [{"concept_id": "concept_fail", "question_id": "q_f"}]
    schedule_module_concepts_for_review("test_learner", "module_1", concepts, db_path=temp_db)
    
    rows = execute_query("SELECT id FROM quiz_reviews WHERE concept_id = 'concept_fail'", db_path=temp_db)
    rev_id = rows[0]["id"]
    
    # Advance to interval 7
    record_review_result(rev_id, score=90.0, passed=True, db_path=temp_db)
    record_review_result(rev_id, score=90.0, passed=True, db_path=temp_db)
    
    # Now fail review (<80%)
    res_fail = record_review_result(rev_id, score=60.0, passed=False, db_path=temp_db)
    assert res_fail["next_interval"] == 1
    assert res_fail["status"] == "due"
