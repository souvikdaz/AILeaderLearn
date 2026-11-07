import io
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import duckdb
import pandas as pd
from config.settings import PROJECT_ROOT
from core.db import execute_write, get_db_connection

LAB_TIMEOUT_SECONDS = 5

def run_sql_lab(
    query: str,
    tables: Dict[str, str],
    db_type: str = "duckdb"
) -> Dict[str, Any]:
    """
    Executes a SQL query in an in-memory DuckDB sandbox with loaded CSV tables.
    """
    # Basic sanity checks to prevent file operations or attaching external DBs
    prohibited_keywords = ["COPY ", "EXPORT ", "ATTACH ", "INSTALL ", "LOAD ", "CALL ", "IMPORT "]
    upper_query = query.upper()
    for kw in prohibited_keywords:
        if kw in upper_query:
            return {
                "success": False,
                "error": f"Security restriction: Command '{kw.strip()}' is prohibited in the lab sandbox.",
                "output": None,
                "row_count": 0
            }
            
    con = duckdb.connect(database=":memory:")
    try:
        # Register provided tables
        for table_name, rel_path in tables.items():
            full_path = PROJECT_ROOT / rel_path
            if full_path.exists():
                con.execute(f"CREATE TABLE {table_name} AS SELECT * FROM read_csv_auto('{full_path}');")
            else:
                return {
                    "success": False,
                    "error": f"Underlying sample data table '{table_name}' not found at {rel_path}.",
                    "output": None,
                    "row_count": 0
                }
                
        # Execute learner's query
        df_result = con.execute(query).df()
        output_str = df_result.to_string(index=False)
        return {
            "success": True,
            "error": None,
            "output": output_str,
            "dataframe": df_result,
            "columns": list(df_result.columns),
            "row_count": len(df_result)
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "output": None,
            "row_count": 0
        }
    finally:
        con.close()

def run_python_lab(
    code: str,
    timeout: int = LAB_TIMEOUT_SECONDS
) -> Dict[str, Any]:
    """
    Runs Python code in an isolated subprocess with a strict execution timeout.
    """
    # Prohibit dangerous OS / network / socket imports in code
    prohibited_modules = ["socket", "urllib", "requests", "http.client", "ftplib", "subprocess", "shutil"]
    for mod in prohibited_modules:
        if f"import {mod}" in code or f"from {mod}" in code:
            return {
                "success": False,
                "error": f"Security restriction: Network/OS library '{mod}' is prohibited in the lab sandbox.",
                "output": ""
            }

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_script = Path(tmp_dir) / "lab_exec.py"
        with open(tmp_script, "w", encoding="utf-8") as f:
            f.write(code)

        # Environment without internet access proxies
        env = os.environ.copy()
        env["PYTHONPATH"] = str(PROJECT_ROOT)
        env["HTTP_PROXY"] = "http://127.0.0.1:0"
        env["HTTPS_PROXY"] = "http://127.0.0.1:0"

        try:
            result = subprocess.run(
                [sys.executable, str(tmp_script)],
                cwd=str(PROJECT_ROOT),
                capture_output=True,
                text=True,
                timeout=timeout,
                env=env
            )
            stdout = result.stdout
            stderr = result.stderr

            if result.returncode != 0:
                return {
                    "success": False,
                    "error": stderr if stderr else f"Process exited with code {result.returncode}",
                    "output": stdout
                }
            return {
                "success": True,
                "error": None,
                "output": stdout
            }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": f"Execution timed out ({timeout}s limit exceeded). Check for infinite loops or non-terminating operations.",
                "output": ""
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "output": ""
            }

def verify_explain_line(
    explanation: str,
    rubric_keywords: List[str],
    min_words: int = 10
) -> Tuple[bool, str]:
    """
    Validates the learner's 'explain this line' submission.
    Requires minimum length and relevant conceptual vocabulary.
    """
    words = explanation.strip().split()
    if len(words) < min_words:
        return False, f"Explanation is too brief ({len(words)} words). Please provide a thorough explanation of at least {min_words} words explaining the business and technical purpose of this line."
        
    lower_exp = explanation.lower()
    matches = [kw for kw in rubric_keywords if kw.lower() in lower_exp]
    
    # Require at least 2 key concepts or 40% keyword match
    required_matches = min(2, max(1, len(rubric_keywords) // 2))
    if len(matches) >= required_matches:
        return True, "Explanation verified! Key technical and business concepts correctly articulated."
    else:
        return False, f"Your explanation needs to address key concepts (e.g. {', '.join(rubric_keywords[:3])}). Explain what happens to the data and downstream executive reporting if this line is omitted."

def record_lab_attempt(
    learner_id: str,
    module_id: str,
    lab_id: str,
    code_submitted: str,
    execution_status: str,
    output: str,
    explain_prompt: str,
    explain_answer: str,
    explain_passed: bool,
    db_path: Optional[Path] = None
) -> Dict[str, Any]:
    """
    Saves a lab execution attempt and updates lab completion status.
    """
    now = datetime.now().isoformat()
    explain_passed_int = 1 if explain_passed else 0
    
    # Find existing attempts
    sql_count = "SELECT COUNT(*) as count FROM lab_attempts WHERE learner_id = ? AND lab_id = ?"
    from core.db import execute_query
    rows = execute_query(sql_count, (learner_id, lab_id), db_path=db_path)
    attempt_num = (rows[0]["count"] + 1) if rows else 1
    
    sql = """
    INSERT INTO lab_attempts (learner_id, module_id, lab_id, code_submitted, execution_status, output, explain_line_prompt, explain_line_answer, explain_line_passed, attempt_number, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    execute_write(sql, (
        learner_id, module_id, lab_id, code_submitted, execution_status,
        output, explain_prompt, explain_answer, explain_passed_int, attempt_num, now
    ), db_path=db_path)
    
    # If execution succeeded AND explain line passed, mark lab as passed in module_progress
    if execution_status == "success" and explain_passed:
        sql_mod = "UPDATE module_progress SET lab_status = 'passed' WHERE learner_id = ? AND module_id = ?"
        execute_write(sql_mod, (learner_id, module_id), db_path=db_path)
        
    return {
        "attempt_number": attempt_num,
        "execution_status": execution_status,
        "explain_passed": explain_passed,
        "lab_passed": (execution_status == "success" and explain_passed)
    }
