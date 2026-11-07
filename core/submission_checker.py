import json
import os
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from config.settings import PROJECT_ROOT, SUBMISSIONS_DIR
from core.db import execute_write, get_db_connection

def extract_file_text(file_path: Path) -> str:
    """Extracts text content from various supported document formats."""
    ext = file_path.suffix.lower()
    
    if ext in [".txt", ".md", ".sql", ".py", ".csv"]:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
            
    elif ext == ".docx":
        try:
            import docx
            doc = docx.Document(file_path)
            full_text = []
            for para in doc.paragraphs:
                full_text.append(para.text)
            for table in doc.tables:
                for row in table.rows:
                    row_text = [cell.text.strip() for cell in row.cells]
                    full_text.append(" | ".join(row_text))
            return "\n".join(full_text)
        except Exception as e:
            return f"Error extracting DOCX text: {e}"
            
    elif ext == ".pptx":
        try:
            from pptx import Presentation
            prs = Presentation(file_path)
            slides_text = []
            for idx, slide in enumerate(prs.slides):
                slide_content = [f"--- Slide {idx + 1} ---"]
                for shape in slide.shapes:
                    if hasattr(shape, "text") and shape.text:
                        slide_content.append(shape.text)
                slides_text.append("\n".join(slide_content))
            return "\n\n".join(slides_text)
        except Exception as e:
            return f"Error extracting PPTX text: {e}"
            
    elif ext == ".ipynb":
        try:
            import nbformat
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                nb = nbformat.read(f, as_version=4)
            nb_text = []
            for cell in nb.cells:
                if cell.cell_type in ["markdown", "code"]:
                    nb_text.append(cell.source)
            return "\n\n".join(nb_text)
        except Exception as e:
            return f"Error extracting IPYNB text: {e}"
            
    elif ext == ".pdf":
        # Basic text scan
        with open(file_path, "rb") as f:
            content = f.read().decode("latin1", errors="ignore")
            # Extract printable ascii runs
            printable = re.findall(r"[A-Za-z0-9\s.,;:'\"()\-–—]{4,}", content)
            return " ".join(printable[:3000])
            
    return ""

def run_project_autochecks(
    file_path: Path,
    project_config: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Executes automated structural and content checks on the submitted file.
    """
    ext = file_path.suffix.lower()
    text = extract_file_text(file_path)
    words = len(text.split())
    
    checks = []
    
    # Check 1: Allowed extension
    allowed_exts = project_config.get("allowed_extensions", [])
    if allowed_exts:
        passed_ext = (ext in allowed_exts)
        checks.append({
            "name": "File Extension Check",
            "passed": passed_ext,
            "detail": f"File type '{ext}' allowed: {allowed_exts}" if passed_ext else f"File type '{ext}' not in allowed list: {allowed_exts}"
        })
        
    # Check 2: Word count
    min_words = project_config.get("min_words", 200)
    max_words = project_config.get("max_words", 2000)
    passed_words = (min_words <= words <= max_words)
    checks.append({
        "name": "Length & Detail Check",
        "passed": passed_words,
        "detail": f"Word count ({words} words) is within target range ({min_words} - {max_words} words)." if passed_words else f"Word count ({words} words) outside target range ({min_words} - {max_words} words)."
    })
    
    # Check 3: Required sections
    req_sections = project_config.get("required_sections", [])
    if req_sections:
        missing_sections = []
        lower_text = text.lower()
        for sec in req_sections:
            if sec.lower() not in lower_text:
                missing_sections.append(sec)
        passed_sections = (len(missing_sections) == 0)
        checks.append({
            "name": "Required Sections Coverage",
            "passed": passed_sections,
            "detail": "All required executive sections identified." if passed_sections else f"Missing required sections: {', '.join(missing_sections)}"
        })
        
    # Check 4: Required keywords
    req_keywords = project_config.get("required_keywords", [])
    if req_keywords:
        missing_keywords = []
        lower_text = text.lower()
        for kw in req_keywords:
            if kw.lower() not in lower_text:
                missing_keywords.append(kw)
        passed_keywords = (len(missing_keywords) <= 1) # allow 1 omission
        checks.append({
            "name": "Technical & Business Terminology",
            "passed": passed_keywords,
            "detail": f"Contains core required terminology ({len(req_keywords) - len(missing_keywords)}/{len(req_keywords)} matched)."
        })
        
    # Check 5: Slide count (for PPTX)
    if ext == ".pptx":
        try:
            from pptx import Presentation
            prs = Presentation(file_path)
            slide_count = len(prs.slides)
            passed_slides = (3 <= slide_count <= 12)
            checks.append({
                "name": "Executive Slide Count",
                "passed": passed_slides,
                "detail": f"Presentation contains {slide_count} slides (Target: 3 - 12 slides)."
            })
        except Exception:
            pass
            
    # Check 6: IPYNB notebook execution check
    if ext == ".ipynb":
        try:
            import nbformat
            with open(file_path, "r", encoding="utf-8") as f:
                nb = nbformat.read(f, as_version=4)
            has_code = any(c.cell_type == "code" for c in nb.cells)
            checks.append({
                "name": "Jupyter Notebook Structure",
                "passed": has_code,
                "detail": f"Notebook parsed successfully with {len(nb.cells)} cells ({sum(1 for c in nb.cells if c.cell_type == 'code')} code cells)."
            })
        except Exception as e:
            checks.append({
                "name": "Jupyter Notebook Validation",
                "passed": False,
                "detail": f"Notebook parsing error: {e}"
            })
            
    # Calculate overall autocheck pass rate
    passed_count = sum(1 for c in checks if c["passed"])
    total_checks = len(checks)
    autochecks_passed = (passed_count >= total_checks - 1) # allow at most 1 minor failure
    
    return {
        "passed": autochecks_passed,
        "score_pct": round((passed_count / total_checks) * 100, 1) if total_checks else 100.0,
        "checks": checks,
        "extracted_text_preview": text[:500] + ("..." if len(text) > 500 else "")
    }

def grade_submission_rubric(
    file_path: Path,
    project_config: Dict[str, Any],
    autocheck_result: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Grades the submission against the rubric criteria.
    Generates 1 key strength and top 2 fixes.
    Pass threshold is >= 80%.
    """
    text = extract_file_text(file_path).lower()
    rubric = project_config.get("rubric", {})
    criteria = rubric.get("criteria", [])
    
    scores = {}
    total_weighted_score = 0.0
    total_weight = 0.0
    
    for crit in criteria:
        cid = crit["id"]
        weight = crit.get("weight", 25)
        total_weight += weight
        
        # Scoring heuristic based on autochecks and keyword density
        base_score = 75.0
        if autocheck_result.get("passed"):
            base_score += 15.0
        else:
            base_score -= 10.0
            
        # Specific criterion boosts
        if "decision" in cid and any(w in text for w in ["recommend", "decision", "proposal", "timeline", "roi"]):
            base_score += 10.0
        if "technical" in cid and any(w in text for w in ["sql", "elt", "join", "pipeline", "dataframe", "metric"]):
            base_score += 10.0
        if "risk" in cid and any(w in text for w in ["risk", "contract", "drift", "sla", "alert", "security"]):
            base_score += 10.0
        if "readability" in cid and len(text.split()) >= 300:
            base_score += 5.0
            
        final_crit_score = min(100.0, max(40.0, base_score))
        scores[cid] = {
            "name": crit["name"],
            "score": round(final_crit_score, 1),
            "weight": weight
        }
        total_weighted_score += (final_crit_score * (weight / 100.0))
        
    final_score = round(total_weighted_score, 1)
    passed = (final_score >= 80.0)
    
    # Strengths and top 2 fixes
    strengths = [
        "Executive alignment: Clearly frames technical architecture in terms of operational risk and commercial P&L impact.",
        "Analytical rigor: Thoroughly diagnoses the failure mechanism and establishes unambiguous data contract requirements.",
        "Strategic clarity: Proposes a concrete, phased roadmap rather than an unmanageable all-at-once migration."
    ]
    
    fixes = [
        "Quantify financial impact: Include concrete dollar estimates (e.g. engineering hours lost, estimated revenue leakage) to strengthen the executive business case.",
        "Explicit SLA thresholds: Codify specific alert thresholds (e.g. 15-minute sync latency, zero-null primary key checks) in the proposed data contracts.",
        "Enhance visual layout: Use bulleted executive takeaways and structured comparison tables to make board scanning effortless."
    ]
    
    selected_strength = strengths[0] if passed else strengths[1]
    selected_fix_1 = fixes[0]
    selected_fix_2 = fixes[1] if not passed else fixes[2]
    
    return {
        "final_score": final_score,
        "passed": passed,
        "criteria_scores": scores,
        "strength": selected_strength,
        "fix_1": selected_fix_1,
        "fix_2": selected_fix_2
    }

def save_and_evaluate_project(
    learner_id: str,
    module_id: str,
    file_name: str,
    file_bytes: bytes,
    project_config: Dict[str, Any],
    db_path: Optional[Path] = None
) -> Dict[str, Any]:
    """
    Saves uploaded file to submissions/<learner_id>/<module_id>/, runs autochecks and rubric evaluation.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    sub_dir = SUBMISSIONS_DIR / learner_id / module_id
    sub_dir.mkdir(parents=True, exist_ok=True)
    
    safe_name = f"{timestamp}_{file_name}"
    target_file = sub_dir / safe_name
    with open(target_file, "wb") as f:
        f.write(file_bytes)
        
    # Run autochecks
    autochecks = run_project_autochecks(target_file, project_config)
    
    # Grade rubric
    grading = grade_submission_rubric(target_file, project_config, autochecks)
    
    # Save to submissions table
    now_iso = datetime.now().isoformat()
    sql = """
    INSERT INTO submissions (learner_id, module_id, file_path, file_name, file_type, auto_check_results, rubric_grade, strength, fix_1, fix_2, score, passed, submitted_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    sub_id = execute_write(sql, (
        learner_id, module_id, str(target_file), file_name, target_file.suffix.lower(),
        json.dumps(autochecks), json.dumps(grading["criteria_scores"]),
        grading["strength"], grading["fix_1"], grading["fix_2"],
        grading["final_score"], 1 if grading["passed"] else 0, now_iso
    ), db_path=db_path)
    
    # Update module_progress table
    proj_status = "passed" if grading["passed"] else "revision_needed"
    sql_mod = """
    UPDATE module_progress
    SET project_score = ?,
        project_status = ?
    WHERE learner_id = ? AND module_id = ?
    """
    execute_write(sql_mod, (grading["final_score"], proj_status, learner_id, module_id), db_path=db_path)
    
    # Check if module can now be fully passed
    from core.mastery_gate import get_module_status, unlock_next_module
    mod_status = get_module_status(learner_id, module_id, db_path=db_path)
    if grading["passed"] and mod_status.get("mastery_score", 0.0) >= 80.0 and mod_status.get("lab_status") == "passed":
        sql_pass = "UPDATE module_progress SET status = 'passed', completed_at = ? WHERE learner_id = ? AND module_id = ?"
        execute_write(sql_pass, (now_iso, learner_id, module_id), db_path=db_path)
        unlock_next_module(learner_id, module_id, db_path=db_path)
        
    return {
        "submission_id": sub_id,
        "file_path": str(target_file),
        "autochecks": autochecks,
        "grading": grading
    }
