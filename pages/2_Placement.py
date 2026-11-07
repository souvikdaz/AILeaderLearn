import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import streamlit as st
import json
from core.placement import (
    load_diagnostic_questions, score_placement_answers,
    record_diagnostic_result, get_learner_diagnostic,
    save_diagnostic_draft, get_diagnostic_draft, delete_diagnostic_draft
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
draft_answers = get_diagnostic_draft(learner_id)

if existing_diagnostic and not st.session_state.get("retake_diagnostic"):
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
        
    st.markdown("---")
    col_nav1, col_nav2 = st.columns([3, 1])
    with col_nav1:
        if st.button("🚀 Proceed to Executive Dashboard", type="primary", use_container_width=True):
            st.switch_page("pages/3_Dashboard.py")
    with col_nav2:
        if st.button("🔄 Retake Diagnostic", use_container_width=True):
            st.session_state["retake_diagnostic"] = True
            st.rerun()

else:
    questions = load_diagnostic_questions()
    total_q = len(questions)
    saved_count = len(draft_answers)
    
    # Mandatory Diagnostic Notice & Progress Banner
    st.info(
        "🔒 **Mandatory Baseline Assessment:** This diagnostic must be submitted to unlock your executive dashboard and curriculum. "
        "You can save your progress and return at any time if you cannot finish in one sitting."
    )
    
    # Progress Bar
    pct_complete = (saved_count / total_q) if total_q > 0 else 0.0
    st.progress(pct_complete, text=f"Diagnostic Progress: {saved_count} of {total_q} questions saved ({int(pct_complete * 100)}%)")
    
    if saved_count > 0:
        st.caption(f"📂 Resuming with {saved_count} saved answers from your last session.")

    with st.form("placement_form", clear_on_submit=False):
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
                        
                    # Pre-fill from draft answers if present
                    initial_idx = draft_answers.get(qid)
                    if initial_idx is not None and not (0 <= initial_idx < len(q["options"])):
                        initial_idx = None
                        
                    selected = st.radio(
                        label="Select your answer:",
                        options=range(len(q["options"])),
                        format_func=lambda i: q["options"][i],
                        key=f"diag_opt_{qid}",
                        index=initial_idx
                    )
                    user_answers[qid] = selected
                    st.markdown("---")
                    
        col_btn1, col_btn2 = st.columns([1, 1])
        with col_btn1:
            save_draft_btn = st.form_submit_button("💾 Save Progress & Continue Later", type="secondary", use_container_width=True)
        with col_btn2:
            submit_diag = st.form_submit_button("🏁 Submit Diagnostic & Unlock Curriculum", type="primary", use_container_width=True)
        
        if save_draft_btn:
            save_diagnostic_draft(learner_id, user_answers)
            answered_now = len([v for v in user_answers.values() if v is not None])
            st.success(f"✅ Progress saved! {answered_now} of {total_q} answers recorded. You can safely log out and return anytime.")
            st.rerun()
            
        if submit_diag:
            unanswered = [qid for qid, ans in user_answers.items() if ans is None]
            # Auto-save whatever answers they have so far
            save_diagnostic_draft(learner_id, user_answers)
            
            if unanswered:
                st.error(
                    f"⚠️ Please complete all questions before final submission ({len(unanswered)} of {total_q} remaining). "
                    "Your current selections have been saved. Use 'Save Progress & Continue Later' if you need to take a break."
                )
            else:
                with st.spinner("Grading placement diagnostic against leadership rubrics..."):
                    result = record_diagnostic_result(learner_id, user_answers)
                    delete_diagnostic_draft(learner_id)
                    st.session_state["retake_diagnostic"] = False
                    st.success("🎉 Placement diagnostic graded and verified! Your custom 90-day curriculum is now unlocked.")
                    st.rerun()
