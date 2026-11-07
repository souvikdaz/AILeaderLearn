import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import streamlit as st
import json
from config.settings import load_track_config
from core.db import get_learner, execute_query
from core.tutor_engine import (
    load_module_lessons, get_lesson_progress, evaluate_check_answer,
    record_lesson_action, generate_tutor_response
)
from core.mastery_gate import can_access_module, get_module_status

st.title("📖 Learn & Interactive AI Tutor")

learner_id = st.session_state.get("active_learner_id")
if not learner_id:
    st.warning("Please select or create a learner profile on the Home page.")
    st.stop()

learner = get_learner(learner_id)
track = load_track_config()

# Module selector (Any accessible module across phases)
all_modules = []
for phase in track.get("phases", []):
    for m in phase.get("modules", []):
        mid = m["id"]
        st_info = get_module_status(learner_id, mid)
        if st_info.get("status") in ["in_progress", "passed", "tested_out", "needs_review"]:
            all_modules.append(m)

if not all_modules:
    all_modules = [track.get("phases", [])[0].get("modules", [])[0]]

mod_options = {m["id"]: f"{m.get('code', 'M')}: {m['title']}" for m in all_modules}
selected_module_id = st.selectbox(
    "Select Module:",
    options=list(mod_options.keys()),
    format_func=lambda x: mod_options[x],
    key="learn_module_selector"
)

# Load lessons for selected module
lessons = load_module_lessons(selected_module_id)
if not lessons:
    st.info("Module lessons are being authored or outlined. Select a Phase 1 module (M1 to M4).")
    st.stop()

# Lesson selector tabs / pills
lesson_titles = [f"L{idx+1}: {l['title']}" for idx, l in enumerate(lessons)]
selected_tab_idx = st.radio(
    "Lessons:",
    options=range(len(lessons)),
    format_func=lambda i: lesson_titles[i],
    horizontal=True,
    key=f"lesson_tabs_{selected_module_id}"
)

current_lesson = lessons[selected_tab_idx]
lesson_id = current_lesson["id"]
progress = get_lesson_progress(learner_id, selected_module_id, lesson_id)

st.markdown("---")
st.markdown(f"### {current_lesson['title']}")
st.caption(f"Estimated Time: {current_lesson.get('estimated_minutes', 15)} mins | Status: **{progress.get('status', 'not_started').upper()}**")

# Plain Language Concept Header
col_c1, col_c2 = st.columns([2, 1])
with col_c1:
    st.markdown(f"**Core Concept:** {current_lesson.get('concept', '')}")
    st.info(f"💡 **Definition:** {current_lesson.get('definition', '')}")
with col_c2:
    st.markdown(f"🎯 **Why Leaders Care:**")
    st.write(current_lesson.get('why_it_matters', ''))

# Lesson Explanation (<300 words)
with st.container():
    st.markdown("#### 📘 The Executive Explanation")
    st.markdown(current_lesson.get("explanation", ""))
    
    if current_lesson.get("analogy"):
        st.markdown(f"> **Analogy:** {current_lesson['analogy']}")

# Worked Example (with code & line-by-line explanation)
worked = current_lesson.get("worked_example")
if worked:
    st.markdown("#### 🔬 Worked Real-World Example")
    st.caption(worked.get("context", ""))
    
    code = worked.get("code_or_query")
    if code:
        lang = "sql" if "SELECT" in code.upper() else "python"
        st.code(code, language=lang)
        
        with st.expander("🔍 Line-by-Line Plain English Explanation", expanded=True):
            for item in worked.get("line_by_line", []):
                st.markdown(f"- ` {item.get('line', '')} ` ➔ **{item.get('explanation', '')}**")

# The Leader's Questions (Interview / Team Audit checklist)
l_questions = current_lesson.get("leader_questions")
if l_questions:
    with st.expander("👔 The Leader's Audit Checklist: What to Ask Your Team", expanded=False):
        st.markdown(f"**What to ask:** *\"{l_questions.get('what_to_ask', '')}\"*")
        st.markdown(f"- 🟢 **What a good answer sounds like:** {l_questions.get('good_answer', '')}")
        st.markdown(f"- 🔴 **Red flag answer:** {l_questions.get('red_flag', '')}")

st.markdown("---")

# Tutor Interactive Dialogue & Check Questions
st.markdown("### 💬 Interactive Tutor Dialogue & Check Questions")
st.caption("Answer the check question below to test your understanding. The AI tutor diagnoses misconceptions in real-time.")

# Display existing chat history
chat_history = progress.get("chat_history", [])
for msg in chat_history:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Check questions
checks = current_lesson.get("check_questions", [])
if checks:
    q = checks[0] # primary concept check
    st.markdown(f"**Check Question:** {q['prompt']}")
    
    opts = q.get("options", [])
    user_choice = st.radio(
        "Choose the best leadership response:",
        options=range(len(opts)),
        format_func=lambda i: opts[i],
        key=f"check_radio_{lesson_id}",
        index=None
    )
    
    col_btn1, col_btn2, col_btn3, col_btn4 = st.columns(4)
    with col_btn1:
        submit_answer = st.button("Submit Answer", type="primary", key=f"btn_sub_{lesson_id}")
    with col_btn2:
        explain_again = st.button("Explain Again 🔄", key=f"btn_exp_{lesson_id}")
    with col_btn3:
        more_practice = st.button("More Practice 🏋️", key=f"btn_prac_{lesson_id}")
    with col_btn4:
        skip_lesson = st.button("Skip Concept ⏭️", key=f"btn_skip_{lesson_id}")

    if submit_answer:
        if user_choice is None:
            st.warning("Please select an option before submitting.")
        else:
            with st.spinner("Tutor evaluating your response against executive rubrics..."):
                eval_res = evaluate_check_answer(
                    learner_id, selected_module_id, lesson_id, q, user_choice
                )
                # Append to chat
                chat_history.append({"role": "user", "content": f"Selected option: {opts[user_choice]}"})
                chat_history.append({"role": "assistant", "content": eval_res["response_text"]})
                
                # If correct, complete lesson
                action = "complete" if eval_res["is_correct"] else "in_progress"
                record_lesson_action(learner_id, selected_module_id, lesson_id, action, chat_history)
                st.rerun()

    if explain_again:
        with st.spinner("AI Tutor simplifying concept..."):
            reply = generate_tutor_response("Explain again simply with an analogy", current_lesson, chat_history)
            chat_history.append({"role": "user", "content": "Can you explain this again in simpler terms?"})
            chat_history.append({"role": "assistant", "content": reply})
            record_lesson_action(learner_id, selected_module_id, lesson_id, "explain_again", chat_history)
            st.rerun()

    if more_practice:
        with st.spinner("Generating scenario drill..."):
            reply = generate_tutor_response("Give me more practice on this scenario", current_lesson, chat_history)
            chat_history.append({"role": "user", "content": "I want more practice on this concept."})
            chat_history.append({"role": "assistant", "content": reply})
            record_lesson_action(learner_id, selected_module_id, lesson_id, "more_practice", chat_history)
            st.rerun()

    if skip_lesson:
        chat_history.append({"role": "user", "content": "Skipped this lesson for now."})
        chat_history.append({"role": "assistant", "content": "⚠️ *Concept skipped. Note: All skipped concepts must still be tested and passed on the Module Mastery Check before the next module unlocks.*"})
        record_lesson_action(learner_id, selected_module_id, lesson_id, "skip", chat_history)
        st.warning("Concept skipped and logged to database.")
        st.rerun()

# Free-form Ask Tutor Chat
user_chat_input = st.chat_input("Ask your AI Tutor a question about this lesson...")
if user_chat_input:
    chat_history.append({"role": "user", "content": user_chat_input})
    with st.spinner("Tutor thinking..."):
        tutor_reply = generate_tutor_response(user_chat_input, current_lesson, chat_history)
        chat_history.append({"role": "assistant", "content": tutor_reply})
        record_lesson_action(learner_id, selected_module_id, lesson_id, "chat", chat_history)
        st.rerun()
