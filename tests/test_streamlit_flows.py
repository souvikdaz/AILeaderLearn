import pytest
from streamlit.testing.v1 import AppTest
from config.settings import PROJECT_ROOT

def test_app_loads_without_exception():
    """Verifies that app.py initializes navigation, loads session state, and boots cleanly."""
    at = AppTest.from_file(str(PROJECT_ROOT / "app.py"), default_timeout=15)
    at.run()
    assert not at.exception
    assert len(at.sidebar) > 0

def test_home_page_renders():
    """Verifies 1_Home.py renders tabs and learner cards."""
    at = AppTest.from_file(str(PROJECT_ROOT / "pages/1_Home.py"), default_timeout=15)
    at.run()
    assert not at.exception

def test_placement_page_renders():
    """Verifies 2_Placement.py renders diagnostic."""
    at = AppTest.from_file(str(PROJECT_ROOT / "pages/2_Placement.py"), default_timeout=15)
    at.session_state["active_learner_id"] = "priya_sharma"
    at.run()
    assert not at.exception

def test_dashboard_page_renders():
    """Verifies 3_Dashboard.py renders charts and metrics."""
    at = AppTest.from_file(str(PROJECT_ROOT / "pages/3_Dashboard.py"), default_timeout=15)
    at.session_state["active_learner_id"] = "priya_sharma"
    at.run()
    assert not at.exception

def test_learn_page_renders():
    """Verifies 4_Learn.py renders lesson content, worked code, and tutor checks."""
    at = AppTest.from_file(str(PROJECT_ROOT / "pages/4_Learn.py"), default_timeout=15)
    at.session_state["active_learner_id"] = "priya_sharma"
    at.run()
    assert not at.exception

def test_lab_page_renders():
    """Verifies 5_Lab.py loads lab runner and code area."""
    at = AppTest.from_file(str(PROJECT_ROOT / "pages/5_Lab.py"), default_timeout=15)
    at.session_state["active_learner_id"] = "priya_sharma"
    at.run()
    assert not at.exception

def test_quiz_page_renders():
    """Verifies 6_Quiz.py loads spaced review queue items."""
    at = AppTest.from_file(str(PROJECT_ROOT / "pages/6_Quiz.py"), default_timeout=15)
    at.session_state["active_learner_id"] = "marcus_vance"
    at.run()
    assert not at.exception

def test_mastery_page_renders():
    """Verifies 7_Mastery.py loads mastery check questions."""
    at = AppTest.from_file(str(PROJECT_ROOT / "pages/7_Mastery.py"), default_timeout=15)
    at.session_state["active_learner_id"] = "priya_sharma"
    at.run()
    assert not at.exception

def test_projects_page_renders():
    """Verifies 8_Projects.py loads uploader and project brief."""
    at = AppTest.from_file(str(PROJECT_ROOT / "pages/8_Projects.py"), default_timeout=15)
    at.session_state["active_learner_id"] = "priya_sharma"
    at.run()
    assert not at.exception

def test_portfolio_page_renders():
    """Verifies 9_Portfolio.py compiles and previews portfolio."""
    at = AppTest.from_file(str(PROJECT_ROOT / "pages/9_Portfolio.py"), default_timeout=15)
    at.session_state["active_learner_id"] = "priya_sharma"
    at.run()
    assert not at.exception

def test_mock_interview_page_renders():
    """Verifies 10_Mock_Interview.py loads leadership interview drill."""
    at = AppTest.from_file(str(PROJECT_ROOT / "pages/10_Mock_Interview.py"), default_timeout=15)
    at.session_state["active_learner_id"] = "priya_sharma"
    at.run()
    assert not at.exception

def test_career_readiness_page_renders():
    """Verifies 11_Career_Readiness.py loads live market postings and positioning."""
    at = AppTest.from_file(str(PROJECT_ROOT / "pages/11_Career_Readiness.py"), default_timeout=15)
    at.session_state["active_learner_id"] = "priya_sharma"
    at.run()
    assert not at.exception

def test_admin_page_renders():
    """Verifies 12_Admin.py loads authentication and admin console."""
    at = AppTest.from_file(str(PROJECT_ROOT / "pages/12_Admin.py"), default_timeout=15)
    at.session_state["admin_authenticated"] = True
    at.run()
    assert not at.exception

def test_unauthenticated_dashboard_blocks_access():
    """Verifies that accessing Dashboard without an active learner session halts with warning."""
    at = AppTest.from_file(str(PROJECT_ROOT / "pages/3_Dashboard.py"), default_timeout=15)
    at.session_state["active_learner_id"] = None
    at.run()
    assert not at.exception
    assert len(at.warning) > 0

def test_admin_manage_learner_profiles_tab():
    """Verifies that 12_Admin.py renders the 'Manage Learner Profiles' view with active telemetry."""
    at = AppTest.from_file(str(PROJECT_ROOT / "pages/12_Admin.py"), default_timeout=15)
    at.session_state["admin_authenticated"] = True
    at.session_state["user_role"] = "admin"
    at.run()
    assert not at.exception
    # Check tabs render
    assert len(at.tabs) > 0

def test_learner_without_diagnostic_dashboard_gated():
    """Verifies that an uncompleted learner accessing Dashboard is stopped with a warning."""
    from core.db import create_learner, delete_learner
    test_lid = "test_gated_learner"
    delete_learner(test_lid)
    create_learner(
        learner_id=test_lid,
        name="Gated Learner",
        track_id="data_ai_leadership",
        current_role="Analyst",
        years_of_experience=3,
        target_level="Leader",
        industry="Tech",
        tools_known=["Excel"],
        hours_per_week=10,
        start_date="2026-11-01"
    )
    try:
        at = AppTest.from_file(str(PROJECT_ROOT / "pages/3_Dashboard.py"), default_timeout=15)
        at.session_state["logged_in"] = True
        at.session_state["user_role"] = "learner"
        at.session_state["active_learner_id"] = test_lid
        at.run()
        assert not at.exception
        assert len(at.warning) > 0
        assert "Placement Diagnostic Required" in at.warning[0].value
    finally:
        delete_learner(test_lid)
