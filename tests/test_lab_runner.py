import pytest
import tempfile
from pathlib import Path
from core.db import init_db, create_learner
from core.lab_runner import (
    run_sql_lab, run_python_lab, verify_explain_line, record_lab_attempt
)

def test_run_sql_lab_success():
    tables = {"customers": "content/sample_data/customers.csv"}
    query = "SELECT customer_id, monthly_spend FROM customers WHERE monthly_spend > 2000;"
    res = run_sql_lab(query, tables)
    assert res["success"] is True
    assert res["row_count"] > 0
    assert "customer_id" in res["columns"]

def test_run_sql_lab_security_block():
    tables = {"customers": "content/sample_data/customers.csv"}
    query = "COPY customers TO 'malicious.csv';"
    res = run_sql_lab(query, tables)
    assert res["success"] is False
    assert "prohibited" in res["error"].lower()

def test_run_python_lab_success():
    code = "import pandas as pd; df = pd.DataFrame({'a': [1, 2]}); print(df['a'].sum())"
    res = run_python_lab(code, timeout=3)
    assert res["success"] is True
    assert "3" in res["output"]

def test_run_python_lab_timeout():
    # Infinite loop code
    code = "import time\nwhile True:\n    time.sleep(0.1)"
    res = run_python_lab(code, timeout=1)
    assert res["success"] is False
    assert "timed out" in res["error"].lower()

def test_verify_explain_line():
    keywords = ["null", "zero", "missing", "coalesce"]
    # Too short
    ok1, msg1 = verify_explain_line("It does nulls.", keywords, min_words=10)
    assert ok1 is False
    assert "too brief" in msg1.lower()
    
    # Adequate length but missing keywords
    ok2, msg2 = verify_explain_line("This line calculates the total revenue from the order table for all accounts.", keywords, min_words=10)
    assert ok2 is False
    
    # Adequate length and includes key concepts
    ok3, msg3 = verify_explain_line("This line uses coalesce to convert null missing values into zero so that executive reports do not show blank data.", keywords, min_words=10)
    assert ok3 is True
