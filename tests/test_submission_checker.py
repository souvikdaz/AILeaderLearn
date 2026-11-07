import pytest
import tempfile
from pathlib import Path
from core.submission_checker import (
    extract_file_text, run_project_autochecks, grade_submission_rubric, save_and_evaluate_project
)
from core.db import init_db, create_learner

def test_extract_file_text():
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as f:
        f.write("# Executive Brief\nThis is a sample brief.")
        temp_path = Path(f.name)
        
    text = extract_file_text(temp_path)
    assert "Executive Brief" in text
    temp_path.unlink()

def test_run_project_autochecks():
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as f:
        f.write(
            "## Executive Summary\n"
            "This report analyzes ELT pipelines, lineage, and data contracts to build a single source of truth in the warehouse. "
            "Words words words words words words words words words words words words words words words words words words. " * 15
        )
        temp_path = Path(f.name)
        
    cfg = {
        "allowed_extensions": [".md", ".docx"],
        "min_words": 50,
        "max_words": 1000,
        "required_sections": ["Executive Summary"],
        "required_keywords": ["ELT", "lineage", "warehouse"]
    }
    res = run_project_autochecks(temp_path, cfg)
    assert res["passed"] is True
    assert len(res["checks"]) >= 4
    temp_path.unlink()

def test_grade_submission_rubric():
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as f:
        f.write(
            "## Executive Summary\n"
            "We recommend transitioning to automated ELT architecture. "
            "The decision provides an immediate ROI by eliminating manual errors and enforcing data contracts and freshness SLAs in our warehouse. " * 8
        )
        temp_path = Path(f.name)
        
    cfg = {
        "rubric": {
            "criteria": [
                {"id": "decision_clarity", "name": "Clarity of Decision", "weight": 50},
                {"id": "technical_accuracy", "name": "Technical Accuracy", "weight": 50}
            ]
        }
    }
    autochecks = {"passed": True}
    res = grade_submission_rubric(temp_path, cfg, autochecks)
    assert res["final_score"] >= 80.0
    assert res["passed"] is True
    assert res["strength"] != ""
    assert res["fix_1"] != ""
    assert res["fix_2"] != ""
    temp_path.unlink()
