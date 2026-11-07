import json
from datetime import datetime, timedelta
from pathlib import Path
import sys

# Ensure project root is in path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.db import (
    init_db, execute_write, execute_query, create_learner, get_all_learners
)
from core.placement import record_diagnostic_result
from core.mastery_gate import record_mastery_attempt, unlock_next_module
from core.lab_runner import record_lab_attempt
from core.submission_checker import save_and_evaluate_project
from core.review_scheduler import schedule_module_concepts_for_review

def seed_database(db_path: Path = None):
    print("Initializing database...")
    init_db(db_path)
    
    now = datetime.now()
    
    # Check if learners already exist
    existing = get_all_learners(db_path)
    if existing:
        print(f"Database already contains {len(existing)} learners. Re-seeding clean state...")
        execute_write("DELETE FROM interview_attempts", db_path=db_path)
        execute_write("DELETE FROM mastery_attempts", db_path=db_path)
        execute_write("DELETE FROM submissions", db_path=db_path)
        execute_write("DELETE FROM lab_attempts", db_path=db_path)
        execute_write("DELETE FROM misconceptions", db_path=db_path)
        execute_write("DELETE FROM quiz_reviews", db_path=db_path)
        execute_write("DELETE FROM lesson_progress", db_path=db_path)
        execute_write("DELETE FROM module_progress", db_path=db_path)
        execute_write("DELETE FROM diagnostic_results", db_path=db_path)
        execute_write("DELETE FROM learners", db_path=db_path)
        
    print("Seeding Learner 1: Priya Sharma (Mid-Phase 1 with failed check and unfinished lab)...")
    p1_start = (now - timedelta(days=12)).date().isoformat()
    l1 = create_learner(
        learner_id="priya_sharma",
        name="Priya Sharma",
        track_id="data_ai_leadership",
        current_role="Senior MIS & Reporting Manager",
        years_of_experience=7,
        target_level="Head of Analytics",
        industry="Retail & E-Commerce",
        tools_known=["Excel (Advanced)", "VBA / Macros", "Power BI", "Basic SQL"],
        hours_per_week=10,
        start_date=p1_start,
        db_path=db_path
    )
    
    # Priya Diagnostic: 63.6% (Starts at Module 1, tests out of none)
    priya_answers = {
        "diag_excel_1": 1, "diag_excel_2": 1, "diag_excel_3": 2, "diag_excel_4": 1, # Excel strong (100%)
        "diag_sql_1": 0, "diag_sql_2": 0, "diag_sql_3": 1, "diag_sql_4": 1, "diag_sql_5": 0, # SQL 40%
        "diag_python_1": 0, "diag_python_2": 1, "diag_python_3": 0, "diag_python_4": 0, # Python 25%
        "diag_ai_1": 1, "diag_ai_2": 1, "diag_ai_3": 1, "diag_ai_4": 0, # AI 75%
        "diag_lead_1": 1, "diag_lead_2": 1, "diag_lead_3": 1, "diag_lead_4": 1, "diag_lead_5": 1, "diag_lead_6": 1 # Lead 100%
    }
    record_diagnostic_result("priya_sharma", priya_answers, db_path=db_path)
    
    # Module 1 Passed for Priya:
    # 1. Lessons completed
    for lid in ["m1_l1", "m1_l2", "m1_l3", "m1_l4"]:
        execute_write(
            "INSERT INTO lesson_progress (learner_id, module_id, lesson_id, status, chat_history, completed_at) VALUES (?, 'module_1', ?, 'completed', '[]', ?)",
            ("priya_sharma", lid, (now - timedelta(days=9)).isoformat()),
            db_path=db_path
        )
    # 2. Lab 1 passed
    record_lab_attempt(
        learner_id="priya_sharma",
        module_id="module_1",
        lab_id="m1_lab",
        code_submitted="SELECT c.customer_id, c.customer_name, c.plan, COALESCE(SUM(o.amount), 0) AS total_order_spend FROM customers c LEFT JOIN orders o ON c.customer_id = o.customer_id AND o.status = 'Completed' WHERE c.is_active = 1 GROUP BY c.customer_id, c.customer_name, c.plan ORDER BY c.customer_id;",
        execution_status="success",
        output="C101 | Acme Logistics | Enterprise | 18900\nC102 | Beta Retail | Professional | 7100\nC104 | Delta Healthcare | Enterprise | 22700\nC106 | Zeta Manufacturing | Professional | 5800\nC107 | Eta SaaS | Enterprise | 20600\nC108 | Theta Edu | Starter | 1100\nC110 | Kappa Energy | Enterprise | 40500",
        explain_prompt="Explain why COALESCE is required here and what happens to non-technical executives reading the dashboard if it is omitted.",
        explain_answer="COALESCE converts NULL values from the LEFT JOIN into 0. Without it, active accounts with zero orders display as blank/NULL, confusing executives into thinking data is missing.",
        explain_passed=True,
        db_path=db_path
    )
    # 3. Project 1 passed
    proj1_content = """# Executive Brief: Enterprise Data Architecture & Flow Bottleneck Audit
Author: Priya Sharma | Head of Analytics Transition Track

## Executive Summary
OmniRetail's recurring Monday reporting crisis was caused by an unannounced schema drift in our upstream POS terminal application, combined with manual Excel copy-paste dependencies. This brief outlines the root cause diagnosis and presents a 60-day architectural transition to an automated ELT pipeline with data contracts.

## Root Cause Analysis of the Monday Incident
The reported 42% revenue decline was an artificial data pipeline defect. Upstream developers renamed 'store_id' to 'pos_terminal_id'. Because our manual MIS workflow relies on fixed column coordinates in Excel VLOOKUPs, the formula returned #N/A for all in-store transactions.

## Architectural Transformation: From Fragile MIS to Modern ELT
We are decommissioning manual spreadsheet extracts in favor of automated ELT:
- Ingestion: Fivetran/Airbyte connectors replicating raw transactional tables into Snowflake.
- Transformation: dbt models standardizing revenue logic and preserving full historical lineage.
- Semantic Layer: Centralized metric catalog providing a single source of truth for all business units.

## Data Contracts & Quality Safeguards
We are implementing automated CI/CD schema validation and Slack alerts on null rates and schema drift.

## Implementation Roadmap & Commercial ROI
Transitioning to automated ELT recovers 80 monthly analyst hours ($72,000 annual capacity gain) and eliminates board-level data discrepancies."""
    
    import yaml
    with open(ROOT / "content/phase_1/module_1_data_flow/project.yaml", "r") as f:
        p1_cfg = yaml.safe_load(f)
    save_and_evaluate_project(
        "priya_sharma", "module_1", "executive_brief_data_flow.md",
        proj1_content.encode("utf-8"), p1_cfg, db_path=db_path
    )
    # 4. Mastery 1 passed (85%)
    record_mastery_attempt(
        "priya_sharma", "module_1", 85.0,
        {"m1_mc_1": 1, "m1_mc_2": 1, "m1_mc_3": 0},
        "We replicate data every 15 minutes into our analytical warehouse, giving real-time visibility without risking live checkout outages.",
        "It returns 0 for order_count because COUNT ignores NULL joined rows.",
        [],
        db_path=db_path
    )
    
    # Schedule Module 1 review concepts
    schedule_module_concepts_for_review("priya_sharma", "module_1", [
        {"concept_id": "oltp_vs_olap", "question_id": "m1_mc_1"},
        {"concept_id": "elt_vs_etl", "question_id": "m1_mc_2"},
        {"concept_id": "data_contracts", "question_id": "m1_mc_3"}
    ], db_path=db_path)
    
    # Module 2 (SQL Leadership) - Priya is currently struggling:
    # - Attempted Lab 2 (incomplete / pending explain line)
    record_lab_attempt(
        learner_id="priya_sharma",
        module_id="module_2",
        lab_id="m2_lab",
        code_submitted="SELECT c.industry, COUNT(c.customer_id) AS customer_count, SUM(o.amount) AS total_revenue FROM customers c JOIN orders o ON c.customer_id = o.customer_id GROUP BY c.industry;",
        execution_status="success",
        output="Energy | 2 | 40500\nFinance | 1 | 18500\nHospitality | 1 | 4300\nLogistics | 2 | 18900\nManufacturing | 1 | 5800\nRetail | 2 | 7100\nTechnology | 2 | 20600",
        explain_prompt="Explain why COUNT(DISTINCT customer_id) is mandatory here rather than COUNT(customer_id).",
        explain_answer="Because I need to count the customers.", # Too brief / fails rubric
        explain_passed=False,
        db_path=db_path
    )
    # - Attempted Mastery 2: Failed at 60% (Attempt 1 of 3)
    record_mastery_attempt(
        "priya_sharma", "module_2", 60.0,
        {"m2_mc_1": 0, "m2_mc_2": 1, "m2_mc_3": 1},
        "A join made the table bigger so the numbers were higher.",
        "Both customers appear.",
        ["Query Execution Order", "Cartesian Fan-out Blindness"],
        db_path=db_path
    )
    
    # Log Priya's misconceptions
    execute_write(
        "INSERT INTO misconceptions (learner_id, module_id, lesson_id, concept, error_type, misconception_name, context, occurred_at) VALUES (?, 'module_2', 'm2_l2', 'SQL Joins', 'relational_multiplication', 'Cartesian Fan-out Blindness', 'Failed to spot duplicate order row multiplication', ?)",
        ("priya_sharma", (now - timedelta(days=2)).isoformat()),
        db_path=db_path
    )
    execute_write(
        "INSERT INTO misconceptions (learner_id, module_id, lesson_id, concept, error_type, misconception_name, context, occurred_at) VALUES (?, 'module_2', 'm2_l1', 'Query Order', 'sql_mental_model', 'Confusing Written Order with Execution Order', 'Used SELECT alias in WHERE clause', ?)",
        ("priya_sharma", (now - timedelta(days=1)).isoformat()),
        db_path=db_path
    )
    
    print("Seeding Learner 2: Marcus Vance (Phase 2 with tested-out modules and active review queue)...")
    p2_start = (now - timedelta(days=28)).date().isoformat()
    l2 = create_learner(
        learner_id="marcus_vance",
        name="Marcus Vance",
        track_id="data_ai_leadership",
        current_role="Commercial Analytics Lead",
        years_of_experience=9,
        target_level="AI Program Lead",
        industry="Financial Services",
        tools_known=["Excel", "Tableau", "Python", "SQL (Intermediate)"],
        hours_per_week=12,
        start_date=p2_start,
        db_path=db_path
    )
    
    # Marcus Diagnostic: 86.4% (Tests out of Module 1 & Module 2!)
    marcus_answers = {
        "diag_excel_1": 1, "diag_excel_2": 1, "diag_excel_3": 2, "diag_excel_4": 1, # 100%
        "diag_sql_1": 1, "diag_sql_2": 1, "diag_sql_3": 1, "diag_sql_4": 1, "diag_sql_5": 1, # 100% -> Tests out M1 & M2!
        "diag_python_1": 1, "diag_python_2": 1, "diag_python_3": 1, "diag_python_4": 1, # 100% -> Tests out M3!
        "diag_ai_1": 1, "diag_ai_2": 1, "diag_ai_3": 1, "diag_ai_4": 1, # 100%
        "diag_lead_1": 1, "diag_lead_2": 1, "diag_lead_3": 1, "diag_lead_4": 1, "diag_lead_5": 1, "diag_lead_6": 1 # 100%
    }
    record_diagnostic_result("marcus_vance", marcus_answers, db_path=db_path)
    
    # Mark Marcus Module 3 and Module 4 passed:
    execute_write("UPDATE module_progress SET status = 'passed', mastery_score = 92.0, lab_status = 'passed', project_score = 90.0, completed_at = ? WHERE learner_id = 'marcus_vance' AND module_id = 'module_3'", ((now - timedelta(days=14)).isoformat(),), db_path=db_path)
    execute_write("UPDATE module_progress SET status = 'passed', mastery_score = 88.0, lab_status = 'passed', project_score = 91.0, completed_at = ? WHERE learner_id = 'marcus_vance' AND module_id = 'module_4'", ((now - timedelta(days=5)).isoformat(),), db_path=db_path)
    
    # Unlock Phase 2 (Module 5):
    execute_write("UPDATE module_progress SET status = 'in_progress', started_at = ? WHERE learner_id = 'marcus_vance' AND module_id = 'module_5'", ((now - timedelta(days=4)).isoformat(),), db_path=db_path)
    
    # Save a sample project for Marcus in Module 4:
    with open(ROOT / "content/phase_1/module_4_metrics_kpis/project.yaml", "r") as f:
        p4_cfg = yaml.safe_load(f)
    proj4_content = """# Enterprise KPI Tree Design & Executive Dashboard Critique
Author: Marcus Vance | Commercial Analytics Lead

## Executive Summary & Situation Overview
CloudScale's Board of Directors was blindsided by an unexpected collapse in Net Revenue Retention (NRR) from 115% to 88%. This failure stems from a dashboard design flaw: tracking 34 vanity operational indicators without a governed, mathematically linked KPI tree.

## The Governed KPI Tree Architecture
We decompose enterprise revenue into a mathematical root:
Root Financial Metric: Ending ARR = Starting ARR + New ARR + Expansion ARR - Churn ARR - Contraction ARR.

## Leading vs Lagging Indicator Framework
- Lagging (Financial): Net Revenue Retention, EBITDA Margin, Gross Margin.
- Leading (Commercial & Product): Feature Adoption Depth (accounts using >= 3 core workflows), Time-to-First-Value (onboarding days), and Support Ticket Aging (> 48h).

## Critical Audit of the Current 34-Chart Dashboard
1. 'All-Time Registered Accounts' is a vanity metric that never decreases, hiding the fact that 60% of accounts were dormant.
2. 'Total Weekly Support Tickets Closed' incentivized agents to rush tickets without solving root bugs, causing repeated re-opens.
3. Lack of unified semantic layer meant Marketing and Finance used conflicting definitions of customer acquisition cost.

## Proposed C-Suite Action Dashboard & Governance Charter
We replace the 34 charts with 5 high-signal decision cards:
1. Trailing 12-Month Net Revenue Retention (Threshold: 110%)
2. 30-Day Active User Stickiness Ratio (DAU / MAU)
3. Leading Churn Risk Index (Predictive Health Score)
4. Customer Acquisition Efficiency (LTV:CAC Ratio)
5. Data Freshness & SLA Alert Matrix"""
    save_and_evaluate_project(
        "marcus_vance", "module_4", "executive_kpi_tree_redesign.md",
        proj4_content.encode("utf-8"), p4_cfg, db_path=db_path
    )
    
    # Add items to Marcus's Spaced Review Queue (Overdue and Due Today):
    today_str = now.strftime("%Y-%m-%d")
    yesterday_str = (now - timedelta(days=2)).strftime("%Y-%m-%d")
    future_str = (now + timedelta(days=5)).strftime("%Y-%m-%d")
    
    execute_write(
        "INSERT INTO quiz_reviews (learner_id, concept_id, module_id, question_id, interval_days, due_date, status, history) VALUES (?, 'leading_vs_lagging_kpis', 'module_4', 'm4_mc_1', 1, ?, 'due', '[]')",
        ("marcus_vance", yesterday_str), db_path=db_path
    ) # Overdue!
    execute_write(
        "INSERT INTO quiz_reviews (learner_id, concept_id, module_id, question_id, interval_days, due_date, status, history) VALUES (?, 'goodharts_law_gaming', 'module_4', 'm4_mc_2', 3, ?, 'due', '[]')",
        ("marcus_vance", today_str), db_path=db_path
    ) # Due Today!
    execute_write(
        "INSERT INTO quiz_reviews (learner_id, concept_id, module_id, question_id, interval_days, due_date, status, history) VALUES (?, 'pandas_boolean_indexing', 'module_3', 'm3_mc_1', 7, ?, 'pending', '[]')",
        ("marcus_vance", future_str), db_path=db_path
    ) # Future!
    
    print("Database seeding completed successfully!")
    print(f"Total learners: {len(get_all_learners(db_path))}")

if __name__ == "__main__":
    seed_database()
