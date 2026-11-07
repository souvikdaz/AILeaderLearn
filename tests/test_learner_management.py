import pytest
from pathlib import Path
from core.db import (
    create_learner, get_learner, delete_learner,
    record_learner_activity, get_learner_last_active,
    get_all_learners_with_activity, execute_write, execute_query
)
from config.settings import PROJECT_ROOT

def test_record_and_get_learner_last_active():
    """Verifies that learner activity is recorded and retrieved properly."""
    lid = "test_active_user"
    create_learner(
        learner_id=lid,
        name="Test Active User",
        track_id="data_ai_leadership",
        current_role="Reporting Analyst",
        years_of_experience=4,
        target_level="Analytics Manager",
        industry="Retail",
        tools_known=["Excel"],
        hours_per_week=10,
        start_date="2026-11-01"
    )
    
    # Record custom activity timestamp
    record_learner_activity(lid, "2026-11-07T14:30:00")
    last_act = get_learner_last_active(lid)
    assert "2026-11-07 14:30:00" in last_act
    
    # Clean up
    delete_learner(lid)

def test_get_all_learners_with_activity():
    """Verifies all learners in database have last_active_date and passed_modules."""
    learners = get_all_learners_with_activity()
    assert len(learners) > 0
    for l in learners:
        assert "last_active_date" in l
        assert l["last_active_date"] != "Never"
        assert "passed_modules" in l
        assert isinstance(l["passed_modules"], int)

def test_delete_learner_cascading():
    """Verifies that delete_learner removes the profile and all related telemetry rows."""
    lid = "test_purge_user"
    create_learner(
        learner_id=lid,
        name="Test Purge User",
        track_id="data_ai_leadership",
        current_role="MIS Analyst",
        years_of_experience=5,
        target_level="Head of Analytics",
        industry="Finance",
        tools_known=["Excel", "SQL"],
        hours_per_week=12,
        start_date="2026-11-01"
    )
    
    # Insert related rows across tables
    execute_write("INSERT INTO module_progress (learner_id, module_id, phase_id, status) VALUES (?, 'module_1', 'phase_1', 'in_progress')", (lid,))
    execute_write("INSERT INTO lesson_progress (learner_id, module_id, lesson_id, status) VALUES (?, 'module_1', 'm1_l1', 'completed')", (lid,))
    execute_write("INSERT INTO lab_attempts (learner_id, module_id, lab_id, code_submitted, execution_status, created_at) VALUES (?, 'module_1', 'm1_lab', 'SELECT 1;', 'success', '2026-11-07T12:00:00')", (lid,))
    execute_write("INSERT INTO diagnostic_results (learner_id, total_score, category_scores, starting_module, tested_out_modules, completed_at) VALUES (?, 75.0, '{}', 'module_1', '[]', '2026-11-07T12:00:00')", (lid,))
    
    # Create fake submission folder
    sub_folder = PROJECT_ROOT / "submissions" / lid
    sub_folder.mkdir(parents=True, exist_ok=True)
    test_file = sub_folder / "test_file.txt"
    test_file.write_text("sample content")
    assert sub_folder.exists()
    
    # Execute deletion
    success = delete_learner(lid)
    assert success is True
    
    # Confirm learner deleted
    assert get_learner(lid) is None
    
    # Confirm relational rows deleted
    for tbl in ["module_progress", "lesson_progress", "lab_attempts", "diagnostic_results"]:
        rows = execute_query(f"SELECT * FROM {tbl} WHERE learner_id = ?", (lid,))
        assert len(rows) == 0, f"Expected 0 rows in {tbl} for {lid}"
        
    # Confirm submission folder removed
    assert not sub_folder.exists()
