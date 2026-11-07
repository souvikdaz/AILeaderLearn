import streamlit as st
import yaml
from pathlib import Path
from config.settings import CONTENT_DIR, load_track_config
from core.db import get_learner, execute_query
from core.mastery_gate import (
    get_module_status, record_mastery_attempt, reset_module, PASS_THRESHOLD, MAX_ATTEMPTS
)

st.title("🏆 Module Mastery Check")
st.markdown(
    "To pass a module, you must achieve **80% or higher** on this comprehensive mastery check "
    "**and** earn a passing score on your capstone project. "
    "Each check includes Multiple Choice, Code Reading, and a C-Suite Executive Explanation. "
    "**Max 3 attempts permitted before a module reset is required.**"
)

learner_id = st.session_state.get("active_learner_id")
if not learner_id:
    st.warning("Please select or create a learner on the Home page.")
    st.stop()

learner = get_learner(learner_id)
track = load_track_config()

# Find all modules with authored mastery.yaml files across all phases
authored_mastery = {}
for p_dir in sorted(CONTENT_DIR.iterdir()):
    if p_dir.is_dir() and p_dir.name.startswith("phase_"):
        for m_dir in sorted(p_dir.iterdir()):
            if m_dir.is_dir() and (m_dir / "mastery.yaml").exists():
                with open(m_dir / "mastery.yaml", "r", encoding="utf-8") as f:
                    mdata = yaml.safe_load(f)
                    mid = mdata.get("module_id")
                    if mid:
                        authored_mastery[mid] = mdata

all_track_mods = []
for phase in track.get("phases", []):
    for m in phase.get("modules", []):
        if m["id"] in authored_mastery:
            all_track_mods.append(m)

mod_options = {m["id"]: f"{m.get('code', 'M')}: {m['title']}" for m in all_track_mods}
selected_module_id = st.selectbox(
    "Select Module for Mastery Check:",
    options=list(mod_options.keys()),
    format_func=lambda x: mod_options[x],
    key="mastery_module_selector"
)

mastery_data = authored_mastery.get(selected_module_id)
if not mastery_data:
    st.info("Mastery questions for this module are currently being loaded.")
    st.stop()

mod_status = get_module_status(learner_id, selected_module_id)
attempts_made = mod_status.get("mastery_attempts", 0)
curr_score = mod_status.get("mastery_score", 0.0)
status = mod_status.get("status", "locked")

col_s1, col_s2, col_s3, col_s4 = st.columns(4)
with col_s1:
    st.metric("Module Status", status.replace('_', ' ').title())
with col_s2:
    st.metric("Latest Score", f"{curr_score}%", f"Threshold: {PASS_THRESHOLD}%")
with col_s3:
    st.metric("Attempts Used", f"{attempts_made} / {MAX_ATTEMPTS}")
with col_s4:
    proj_score = mod_status.get("project_score", 0.0)
    st.metric("Project Score", f"{proj_score}%", "Required: >=80%")

# Reset condition check
if attempts_made >= MAX_ATTEMPTS and curr_score < PASS_THRESHOLD:
    st.error(
        f"⛔ **Max Attempts Reached ({attempts_made}/{MAX_ATTEMPTS}).** "
        f"You have not met the 80% mastery threshold. To preserve learning integrity, "
        f"you must reset this module, review the lesson concepts, and attempt a fresh check."
    )
    if st.button("🔄 Reset Module & Clear Attempts", type="primary"):
        reset_module(learner_id, selected_module_id)
        st.success("Module reset! You may now review lessons and take the check again.")
        st.rerun()
    st.stop()

if status == "passed" or status == "tested_out":
    st.success(f"🎉 **Module Mastery Verified!** You passed with {curr_score}% on attempt #{attempts_made}.")

# Mastery data already loaded from authored_mastery above

questions = mastery_data.get("questions", [])

st.markdown("---")
st.markdown(f"### {mastery_data.get('title', 'Mastery Evaluation')}")
st.caption(f"Attempt #{attempts_made + 1} of {MAX_ATTEMPTS}")

with st.form(f"mastery_form_{selected_module_id}"):
    user_answers = {}
    exec_explanation_text = ""
    code_reading_text = ""

    for idx, q in enumerate(questions):
        qid = q["id"]
        qtype = q.get("type", "multiple_choice")
        points = q.get("points", 20)

        st.markdown(f"#### Question {idx + 1} ({points} pts)")
        st.markdown(q["prompt"])

        if qtype == "multiple_choice":
            opts = q.get("options", [])
            user_answers[qid] = st.radio(
                "Select the best option:",
                options=range(len(opts)),
                format_func=lambda i: opts[i],
                key=f"mc_opt_{qid}",
                index=None
            )
        elif qtype == "code_reading":
            if q.get("code_snippet"):
                st.code(q["code_snippet"], language="sql")
            opts = q.get("options", [])
            user_answers[qid] = st.radio(
                "Based on the code snippet, select the correct prediction:",
                options=range(len(opts)),
                format_func=lambda i: opts[i],
                key=f"code_opt_{qid}",
                index=None
            )
            code_reading_text = f"Selected option index: {user_answers[qid]}"
        elif qtype == "executive_explanation":
            exec_explanation_text = st.text_area(
                "Your Executive Defense (Plain English, written for a non-technical C-suite leader):",
                placeholder="Explain the technical reality using an everyday analogy, reassure the executive on risk, and propose a sound alternative...",
                height=130,
                key=f"exec_text_{qid}"
            )
            user_answers[qid] = exec_explanation_text
            
        st.markdown("---")

    submit_mastery = st.form_submit_button("🏁 Submit Mastery Check for Grading", type="primary")

    if submit_mastery:
        # Check completeness
        unanswered = False
        for q in questions:
            qid = q["id"]
            if q.get("type") != "executive_explanation" and user_answers.get(qid) is None:
                unanswered = True
            elif q.get("type") == "executive_explanation" and len(exec_explanation_text.strip().split()) < 15:
                unanswered = True

        if unanswered:
            st.warning("Please complete all questions (including a thorough executive explanation of >=15 words) before submitting.")
        else:
            with st.spinner("Grading mastery check against executive rubrics..."):
                # Score questions
                earned_points = 0
                total_points = sum(q.get("points", 20) for q in questions)
                weak_concepts = []

                for q in questions:
                    qid = q["id"]
                    qtype = q.get("type")
                    pts = q.get("points", 20)

                    if qtype in ["multiple_choice", "code_reading"]:
                        correct_idx = q.get("correct_index", 0)
                        if user_answers.get(qid) == correct_idx:
                            earned_points += pts
                        else:
                            weak_concepts.append(q.get("concept", "Technical Concept"))
                    elif qtype == "executive_explanation":
                        words = len(exec_explanation_text.split())
                        # Check criteria keywords
                        lower_txt = exec_explanation_text.lower()
                        crit = q.get("evaluation_criteria", [])
                        matches = sum(1 for c in crit if any(w in lower_txt for w in c.lower().split()[:2]))
                        if words >= 25 and matches >= 1:
                            earned_points += pts
                        else:
                            earned_points += int(pts * 0.6)
                            weak_concepts.append("Executive Risk Communication")

                final_score = round((earned_points / total_points) * 100, 1)

                rec = record_mastery_attempt(
                    learner_id=learner_id,
                    module_id=selected_module_id,
                    score=final_score,
                    answers=user_answers,
                    executive_explanation=exec_explanation_text,
                    code_reading_answer=code_reading_text,
                    weak_concepts=weak_concepts
                )

                if rec["passed"]:
                    st.balloons()
                    st.success(f"🎉 **Mastery Passed! Score: {final_score}%** (Attempt #{rec['attempt_number']})")
                else:
                    st.error(f"❌ **Mastery Check Not Passed. Score: {final_score}%** (Threshold: {PASS_THRESHOLD}%)")
                    if weak_concepts:
                        st.markdown(f"**Identified Weak Concepts for Review:** {', '.join(weak_concepts)}")

                st.rerun()

st.markdown("---")
# Attempt History Table
st.markdown("### 📜 Past Mastery Check Attempts")
sql_att = """
SELECT attempt_number, score, passed, weak_concepts, created_at 
FROM mastery_attempts 
WHERE learner_id = ? AND module_id = ?
ORDER BY attempt_number DESC
"""
att_rows = [dict(r) for r in execute_query(sql_att, (learner_id, selected_module_id))]
if att_rows:
    for a in att_rows:
        icon = "🟢 Passed" if a["passed"] else "🔴 Failed"
        st.markdown(f"- **Attempt #{a['attempt_number']}:** {a['score']}% — {icon} ({a['created_at'][:16]}) | Weak: `{a.get('weak_concepts', '[]')}`")
else:
    st.caption("No previous mastery check attempts recorded.")
