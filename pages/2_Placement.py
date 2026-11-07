import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import streamlit as st
import json
from core.placement import (
    load_diagnostic_questions, score_placement_answers,
    record_diagnostic_result, get_learner_diagnostic
)
from core.db import get_learner

st.title("🧭 Placement Diagnostic")
st.markdown(
    "This 22-question diagnostic benchmarks your foundational knowledge across **Excel to Architecture**, "
    "**SQL Query Reading**, **Python/pandas**, **AI Concepts**, and **Leadership Scenarios**. "
    "Your score determines your custom starting module and allows you to test out of passed foundational modules."
)

learner_id = st.session_state.get("active_learner_id")
if not learner_id:
    st.warning("Please select or create a learner profile on the Home page first.")
    st.stop()

learner = get_learner(learner_id)
existing_diagnostic = get_learner_diagnostic(learner_id)

if existing_diagnostic:
    st.success(f"✅ Diagnostic completed for **{learner['name']}** on {existing_diagnostic['completed_at'][:10]}.")
    
    col_score1, col_score2, col_score3 = st.columns(3)
    with col_score1:
        st.metric("Overall Score", f"{existing_diagnostic['total_score']}%")
    with col_score2:
        st.metric("Starting Module", existing_diagnostic['starting_module'].replace('_', ' ').title())
    with col_score3:
        tested_out = existing_diagnostic.get("tested_out_modules", [])
        st.metric("Modules Tested Out", len(tested_out))
        
    st.markdown("### Category Competency Breakdown")
    cat_scores = existing_diagnostic.get("category_scores", {})
    cols_cat = st.columns(len(cat_scores))
    for idx, (cat_name, data) in enumerate(cat_scores.items()):
        with cols_cat[idx % len(cols_cat)]:
            display_name = cat_name.replace('_', ' ').title()
            pct = data.get("pct", 0)
            st.metric(display_name, f"{pct}%", f"{data.get('correct')}/{data.get('total')} correct")
            
    if tested_out:
        st.info(f"🎉 Based on your verified score, you have tested out of: **{', '.join([m.replace('_', ' ').title() for m in tested_out])}**.")
    else:
        st.info("You will start at **Module 1: How Data Flows Through a Business**.")
        
    if st.button("🔄 Retake Placement Diagnostic"):
        st.session_state["retake_diagnostic"] = True
        st.rerun()

if not existing_diagnostic or st.session_state.get("retake_diagnostic"):
    questions = load_diagnostic_questions()
    st.markdown(f"### Diagnostic Questions ({len(questions)} Scenarios)")
    st.caption("Answer candidly. Scenario-based questions evaluate how you reason about technical trade-offs.")
    
    with st.form("placement_form"):
        user_answers = {}
        
        # Group questions by category for clear readability
        categories = ["excel_reporting", "sql_reading", "python_reading", "ai_concepts", "leadership_scenarios"]
        cat_labels = {
            "excel_reporting": "Pillar 1: Excel Reporting & Data Architecture Bridge",
            "sql_reading": "Pillar 2: SQL Reading & Query Auditing",
            "python_reading": "Pillar 3: Python & pandas for Leaders",
            "ai_concepts": "Pillar 4: AI & LLM Fundamentals",
            "leadership_scenarios": "Pillar 5: Analytics & AI Leadership Scenarios"
        }
        
        for cat in categories:
            cat_qs = [q for q in questions if q.get("category") == cat]
            if cat_qs:
                st.markdown(f"#### {cat_labels.get(cat, cat.title())}")
                for q in cat_qs:
                    qid = q["id"]
                    st.markdown(f"**{q.get('pillar', 'Scenario')}:** {q['prompt']}")
                    
                    if q.get("is_code_reading") and q.get("snippet"):
                        lang = "sql" if "sql" in qid else "python"
                        st.code(q["snippet"], language=lang)
                        
                    selected = st.radio(
                        label="Select your answer:",
                        options=range(len(q["options"])),
                        format_func=lambda i: q["options"][i],
                        key=f"diag_opt_{qid}",
                        index=None
                    )
                    user_answers[qid] = selected
                    st.markdown("---")
                    
        submit_diag = st.form_submit_button("🏁 Submit Diagnostic & Calculate Starting Track", type="primary")
        
        if submit_diag:
            unanswered = [qid for qid, ans in user_answers.items() if ans is None]
            if unanswered:
                st.error(f"Please answer all questions before submitting. Unanswered: {len(unanswered)} questions.")
            else:
                with st.spinner("Grading placement diagnostic against leadership rubrics..."):
                    result = record_diagnostic_result(learner_id, user_answers)
                    st.session_state["retake_diagnostic"] = False
                    st.success("Diagnostic successfully graded and saved!")
                    st.rerun()
