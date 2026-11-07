import pytest
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from core.db import init_db, create_learner, execute_write
from core.progress_tracker import calculate_learner_metrics

@pytest.fixture
def temp_db():
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_path = Path(tmp_dir) / "test.db"
        init_db(db_path)
        yield db_path

def test_pace_projection_on_track(temp_db):
    # Learner started 10 days ago, has completed 7 lessons (~0.7/day)
    start_date = (datetime.now() - timedelta(days=10)).date().isoformat()
    create_learner(
        learner_id="ontrack_learner",
        name="On Track Learner",
        track_id="data_ai_leadership",
        current_role="Manager",
        years_of_experience=5,
        target_level="Head of Analytics",
        industry="Retail",
        tools_known=["Excel"],
        hours_per_week=10,
        start_date=start_date,
        db_path=temp_db
    )
    for i in range(7):
        execute_write(
            "INSERT INTO lesson_progress (learner_id, module_id, lesson_id, status, completed_at) VALUES ('ontrack_learner', 'module_1', ?, 'completed', ?)",
            (f"l_{i}", datetime.now().isoformat()),
            db_path=temp_db
        )
    
    metrics = calculate_learner_metrics("ontrack_learner", db_path=temp_db)
    assert metrics["days_left"] == 80
    assert metrics["pace_status"] in ["on_track", "ahead"]
    assert "projected_finish_date" in metrics

def test_pace_projection_behind(temp_db):
    # Started 30 days ago, completed only 2 lessons (expected ~20 lessons)
    start_date = (datetime.now() - timedelta(days=30)).date().isoformat()
    create_learner(
        learner_id="behind_learner",
        name="Behind Learner",
        track_id="data_ai_leadership",
        current_role="Manager",
        years_of_experience=5,
        target_level="Head of Analytics",
        industry="Retail",
        tools_known=["Excel"],
        hours_per_week=10,
        start_date=start_date,
        db_path=temp_db
    )
    for i in range(2):
        execute_write(
            "INSERT INTO lesson_progress (learner_id, module_id, lesson_id, status, completed_at) VALUES ('behind_learner', 'module_1', ?, 'completed', ?)",
            (f"l_{i}", datetime.now().isoformat()),
            db_path=temp_db
        )
        
    metrics = calculate_learner_metrics("behind_learner", db_path=temp_db)
    assert metrics["days_left"] == 60
    assert metrics["pace_status"] == "behind"
    assert "Behind" in metrics["pace_label"]
