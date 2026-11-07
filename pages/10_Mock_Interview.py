import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import streamlit as st
import json
from config.settings import load_track_config
from core.db import get_learner, execute_query
from core.mock_interview import (
    LEADERSHIP_INTERVIEW_QUESTIONS, grade_interview_response, record_interview_attempt
)

st.title("🎙️ Mock Leadership Interview")
st.markdown(
    "Practice answering rigorous senior leadership interview questions covering **STAR Behavioral**, "
    "**Strategy & P&L**, **Technical Judgment**, and **Stakeholder Conflict**. "
    "Submit your answer via text or use `st.audio_input` for the 2-minute executive pitch."
)

learner_id = st.session_state.get("active_learner_id")
if not learner_id:
    st.warning("Please select or create a learner on the Home page.")
    st.stop()

learner = get_learner(learner_id)

# Question Selector (10 leadership questions)
q_options = {q["id"]: f"[{q['category']}] {q['title']}" for q in LEADERSHIP_INTERVIEW_QUESTIONS}
selected_qid = st.selectbox(
    "Select Interview Question Drill:",
    options=list(q_options.keys()),
    format_func=lambda x: q_options[x],
    key="interview_question_selector"
)

active_q = next(q for q in LEADERSHIP_INTERVIEW_QUESTIONS if q["id"] == selected_qid)

st.markdown("---")
st.markdown(f"### {active_q['title']}")
st.caption(f"Category: **{active_q['category']}** | Recommended Framework: *{active_q.get('framework', 'STAR')}*")

st.info(f"🗣️ **Interviewer Prompt:** *\"{active_q['prompt']}\"*")

if active_q.get("is_two_minute_drill"):
    st.warning("⏱️ **2-Minute Executive Strategy Drill:** Structure your answer cleanly within 150-300 words (or 2 minutes of spoken audio). Avoid getting bogged down in low-level syntax.")

tab_text, tab_audio, tab_benchmark = st.tabs(["Typed Answer", "Audio Response (st.audio_input)", "Benchmark Strong Response"])

with tab_text:
    text_input = st.text_area(
        "Type your executive response:",
        placeholder="Structure your answer with strategic intent, concrete operational examples, and commercial business outcomes...",
        height=180,
        key=f"interview_text_{selected_qid}"
    )
    if st.button("Submit Typed Response for Grading", type="primary", key=f"btn_text_{selected_qid}"):
        if not text_input.strip():
            st.warning("Please enter an answer before submitting.")
        else:
            with st.spinner("Scoring leadership response against executive rubrics..."):
                eval_res = record_interview_attempt(learner_id, selected_qid, "text", text_input)
                st.markdown("### 📊 Interview Feedback")
                if eval_res["passed"]:
                    st.balloons()
                    st.success(f"🎉 **Strong Performance! Score: {eval_res['score']}%**")
                else:
                    st.warning(f"⚠️ **Score: {eval_res['score']}%** (Needs refinement for executive panel)")
                    
                st.markdown("#### 🌟 Key Strengths:")
                st.info(eval_res["strengths"])
                st.markdown("#### 🛠️ Areas to Strengthen:")
                st.warning(eval_res["fixes"])

with tab_audio:
    st.caption("Record your spoken 2-minute pitch directly using your microphone:")
    audio_val = None
    if hasattr(st, "audio_input"):
        audio_val = st.audio_input("Record your answer", key=f"audio_rec_{selected_qid}")
    else:
        st.info("Audio recording component requires browser microphone permissions.")
        
    if audio_val is not None:
        st.audio(audio_val)
        spoken_transcript = st.text_area(
            "Speech Transcript / Notes for Verification:",
            placeholder="Review or paste your transcribed notes to grade against the rubric...",
            key=f"audio_trans_{selected_qid}"
        )
        if st.button("Grade Audio Delivery", type="primary", key=f"btn_audio_grade_{selected_qid}"):
            if not spoken_transcript.strip():
                st.warning("Please verify your spoken transcript to calculate rubric score.")
            else:
                with st.spinner("Evaluating executive communication delivery..."):
                    eval_res = record_interview_attempt(learner_id, selected_qid, "audio", spoken_transcript)
                    st.success(f"Graded Audio Score: **{eval_res['score']}%**")
                    st.info(eval_res["strengths"])
                    st.warning(eval_res["fixes"])

with tab_benchmark:
    st.markdown("#### Model C-Suite Response")
    st.markdown(f"> *\"{active_q.get('sample_strong_response', '')}\"*")
    st.markdown("#### Critical Rubric Signals Checked by Interviewers:")
    for sig in active_q.get("rubric_criteria", []):
        st.markdown(f"- 🔑 `{sig}`")

st.markdown("---")
# Past Interview Attempts
st.markdown("### 📜 Past Interview Scores for This Question")
sql_past = """
SELECT response_type, score, created_at, feedback 
FROM interview_attempts 
WHERE learner_id = ? AND question_id = ?
ORDER BY id DESC LIMIT 5
"""
past_rows = execute_query(sql_past, (learner_id, selected_qid))
if past_rows:
    for p in past_rows:
        icon = "🟢" if p["score"] >= 80.0 else "🟡"
        st.markdown(f"- {icon} **{p['score']}%** ({p['response_type'].upper()}) — {p['created_at'][:16]}")
else:
    st.caption("No previous attempts recorded for this question.")
