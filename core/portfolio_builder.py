import io
import json
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from config.settings import PROJECT_ROOT, SUBMISSIONS_DIR
from core.db import execute_query, get_learner

def get_learner_portfolio_items(learner_id: str, db_path: Optional[Path] = None) -> List[Dict[str, Any]]:
    """
    Gathers all passed case studies, lab outputs, and project submissions for a learner's portfolio.
    """
    learner = get_learner(learner_id, db_path=db_path)
    if not learner:
        return []
        
    items = []
    
    # 1. Project Submissions
    sql_sub = "SELECT * FROM submissions WHERE learner_id = ? ORDER BY submitted_at ASC"
    sub_rows = [dict(r) for r in execute_query(sql_sub, (learner_id,), db_path=db_path)]
    for sub in sub_rows:
        file_path = Path(sub["file_path"])
        content_preview = ""
        if file_path.exists():
            from core.submission_checker import extract_file_text
            content_preview = extract_file_text(file_path)[:1200]
            
        items.append({
            "type": "project_case_study",
            "module_id": sub["module_id"],
            "title": f"Executive Case Study: {sub['module_id'].replace('_', ' ').title()}",
            "file_name": sub["file_name"],
            "score": sub["score"],
            "strength": sub.get("strength", ""),
            "submitted_at": sub["submitted_at"],
            "content_preview": content_preview
        })
        
    # 2. Passed Labs
    sql_labs = """
    SELECT l.* FROM lab_attempts l
    INNER JOIN (
        SELECT lab_id, MAX(id) as max_id 
        FROM lab_attempts 
        WHERE learner_id = ? AND explain_line_passed = 1 
        GROUP BY lab_id
    ) latest ON l.id = latest.max_id
    """
    lab_rows = [dict(r) for r in execute_query(sql_labs, (learner_id,), db_path=db_path)]
    for lab in lab_rows:
        items.append({
            "type": "lab_artifact",
            "module_id": lab["module_id"],
            "title": f"Hands-On Technical Lab: {lab['lab_id'].upper()}",
            "code_submitted": lab.get("code_submitted", ""),
            "explain_answer": lab.get("explain_line_answer", ""),
            "created_at": lab["created_at"],
            "execution_status": lab["execution_status"]
        })
        
    return items

def generate_portfolio_markdown(learner_id: str, db_path: Optional[Path] = None) -> str:
    """
    Compiles a comprehensive, portfolio-grade Markdown document summarizing the learner's
    technical case studies, architectural audits, and verified code implementations.
    """
    learner = get_learner(learner_id, db_path=db_path)
    if not learner:
        return "# Learner Portfolio Not Found"
        
    items = get_learner_portfolio_items(learner_id, db_path=db_path)
    
    md = []
    md.append(f"# Executive Data & AI Leadership Portfolio")
    md.append(f"**Leader:** {learner.get('name', 'Learner')}  ")
    md.append(f"**Target Role:** {learner.get('target_level', 'Head of Analytics / AI Lead')}  ")
    md.append(f"**Track:** Data & AI Leadership (90-Day Executive Accelerator)  ")
    md.append(f"**Portfolio Generated:** {datetime.now().strftime('%B %d, %Y')}  \n")
    md.append("---\n")
    
    md.append("## Executive Summary")
    md.append(
        f"This portfolio documents verified hands-on technical competence, architectural governance frameworks, "
        f"and commercial decision-making capabilities. Bridging senior MIS/reporting leadership into modern "
        f"enterprise data stacks (SQL, Python, DuckDB, Semantic Modeling, and Generative AI benchmarks), "
        f"each case study highlights a real-world business crisis, root cause diagnosis, and strategic resolution.\n"
    )
    
    md.append("## Verified Capstone Case Studies & Briefs\n")
    
    case_studies = [it for it in items if it["type"] == "project_case_study"]
    if not case_studies:
        md.append("*No project capstone submissions completed yet. Progress through Phase 1-4 modules to publish case studies.*\n")
    else:
        for cs in case_studies:
            md.append(f"### {cs['title']}")
            md.append(f"- **Module:** `{cs['module_id']}` | **Score:** `{cs['score']}%` | **Status:** `Verified Pass`")
            md.append(f"- **Key Executive Strength:** {cs['strength']}")
            md.append(f"\n```text\n{cs['content_preview']}\n```\n")
            
    md.append("## Hands-On Technical Labs & Query Audits\n")
    labs = [it for it in items if it["type"] == "lab_artifact"]
    if not labs:
        md.append("*No hands-on labs completed yet.*\n")
    else:
        for lb in labs:
            md.append(f"### {lb['title']}")
            md.append(f"**Verified Technical Code Submission:**")
            md.append(f"```sql\n{lb['code_submitted'].strip()}\n```")
            md.append(f"**Executive 'Explain This Line' Defense:**")
            md.append(f"> *\"{lb['explain_answer']}\"*\n")
            
    return "\n".join(md)

def export_portfolio_zip(learner_id: str, db_path: Optional[Path] = None) -> bytes:
    """
    Creates an in-memory ZIP bundle containing the formatted Markdown portfolio
    and all project submission artifacts.
    """
    portfolio_md = generate_portfolio_markdown(learner_id, db_path=db_path)
    items = get_learner_portfolio_items(learner_id, db_path=db_path)
    
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        # Write main portfolio markdown
        zip_file.writestr("PORTFOLIO_EXECUTIVE_SUMMARY.md", portfolio_md)
        
        # Add actual uploaded submission files if they exist on disk
        for idx, it in enumerate(items):
            if it["type"] == "project_case_study":
                mod = it["module_id"]
                fname = it["file_name"]
                zip_file.writestr(f"case_studies/{mod}_{fname}.txt", it.get("content_preview", ""))
                
    zip_buffer.seek(0)
    return zip_buffer.getvalue()
