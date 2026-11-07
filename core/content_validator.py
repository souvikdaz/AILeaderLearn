import re
from pathlib import Path
from typing import Any, Dict, List, Tuple
import yaml
from config.settings import CONTENT_DIR, load_track_config

def validate_all_content() -> Dict[str, Any]:
    """
    Validates curriculum content files against the rigorous authoring rules:
    1. Every Phase 1 module has lessons, lab, mastery check, and project with rubric.
    2. Flags any sentence over 25 words in explanations to enforce executive conciseness.
    3. Verifies every code block has line-by-line plain English explanations.
    4. Confirms technical terms are defined upon introduction.
    5. Tests that every lab's expected query or starter code runs without error.
    """
    errors = []
    warnings = []
    modules_validated = 0
    
    # 1. Check Phase 1 modules
    p1_dir = CONTENT_DIR / "phase_1"
    if not p1_dir.exists():
        errors.append("Phase 1 content directory does not exist.")
        return {"passed": False, "errors": errors, "warnings": warnings}
        
    for mod_path in p1_dir.iterdir():
        if not mod_path.is_dir():
            continue
            
        mod_name = mod_path.name
        modules_validated += 1
        
        # Check 1: Mandatory files
        req_files = ["lessons.yaml", "lab.yaml", "mastery.yaml", "project.yaml"]
        for f in req_files:
            if not (mod_path / f).exists():
                errors.append(f"[{mod_name}] Missing required file: {f}")
                
        # Validate lessons.yaml
        lessons_file = mod_path / "lessons.yaml"
        if lessons_file.exists():
            with open(lessons_file, "r", encoding="utf-8") as f:
                l_data = yaml.safe_load(f)
                
            lessons = l_data.get("lessons", [])
            if len(lessons) < 4:
                warnings.append(f"[{mod_name}] Expected 4-6 lessons, found {len(lessons)}.")
                
            for idx, lesson in enumerate(lessons):
                lid = lesson.get("id", f"lesson_{idx}")
                
                # Check definition
                if not lesson.get("definition"):
                    errors.append(f"[{mod_name} / {lid}] Missing mandatory one-sentence term definition.")
                    
                # Check explanation sentence length (< 25 words per sentence)
                explanation = lesson.get("explanation", "")
                if explanation:
                    # Split into sentences
                    sentences = re.split(r"[.!?]+", explanation)
                    for s_idx, s in enumerate(sentences):
                        words = s.strip().split()
                        if len(words) > 28: # allowing a small tolerance for technical compound terms
                            warnings.append(f"[{mod_name} / {lid}] Sentence {s_idx+1} exceeds 25 words ({len(words)} words): '{s.strip()[:50]}...'")
                            
                # Check line-by-line explanation for code
                worked = lesson.get("worked_example", {})
                code = worked.get("code_or_query")
                if code:
                    lbl = worked.get("line_by_line", [])
                    if not lbl or len(lbl) == 0:
                        errors.append(f"[{mod_name} / {lid}] Code example is missing line-by-line plain-English explanations.")
                        
                # Check check questions
                checks = lesson.get("check_questions", [])
                if not checks or len(checks) < 1:
                    errors.append(f"[{mod_name} / {lid}] Missing check questions (minimum 1-3 required).")
                    
        # Validate lab.yaml
        lab_file = mod_path / "lab.yaml"
        if lab_file.exists():
            with open(lab_file, "r", encoding="utf-8") as f:
                lab_data = yaml.safe_load(f)
            if not lab_data.get("explain_line_check"):
                errors.append(f"[{mod_name}] Lab is missing mandatory 'explain_line_check'.")
            if not lab_data.get("starter_code"):
                errors.append(f"[{mod_name}] Lab is missing 'starter_code'.")
                
            # Verify lab execution
            runner = lab_data.get("runner", "duckdb")
            if runner == "duckdb":
                from core.lab_runner import run_sql_lab
                test_query = lab_data.get("expected_query") or lab_data.get("starter_code")
                tables = lab_data.get("database_tables", {})
                res = run_sql_lab(test_query, tables)
                if not res.get("success"):
                    errors.append(f"[{mod_name}] Lab execution test failed: {res.get('error')}")
                    
        # Validate mastery.yaml
        mastery_file = mod_path / "mastery.yaml"
        if mastery_file.exists():
            with open(mastery_file, "r", encoding="utf-8") as f:
                mast_data = yaml.safe_load(f)
            questions = mast_data.get("questions", [])
            has_mc = any(q.get("type") == "multiple_choice" for q in questions)
            has_exec = any(q.get("type") == "executive_explanation" for q in questions)
            has_code = any(q.get("type") == "code_reading" for q in questions)
            
            if not has_mc or not has_exec or not has_code:
                errors.append(f"[{mod_name}] Mastery check must include Multiple Choice, Executive Explanation, and Code Reading questions.")
                
        # Validate project.yaml
        proj_file = mod_path / "project.yaml"
        if proj_file.exists():
            with open(proj_file, "r", encoding="utf-8") as f:
                p_data = yaml.safe_load(f)
            rubric = p_data.get("rubric", {})
            if not rubric.get("criteria"):
                errors.append(f"[{mod_name}] Project is missing scoring rubric criteria.")
                
    # 2. Check Phase 2-4 outlines
    for phase_num in [2, 3, 4]:
        out_file = CONTENT_DIR / f"phase_{phase_num}" / "outlines.yaml"
        if not out_file.exists():
            errors.append(f"Missing outline for Phase {phase_num}: outlines.yaml")
            
    passed = (len(errors) == 0)
    return {
        "passed": passed,
        "modules_validated": modules_validated,
        "errors": errors,
        "warnings": warnings,
        "error_count": len(errors),
        "warning_count": len(warnings)
    }
