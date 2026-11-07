import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import streamlit as st
from datetime import datetime
from config.settings import load_track_config
from core.db import get_learner, execute_query
from core.review_scheduler import get_review_queue, record_review_result

st.title("🔁 Spaced Review Quiz")
st.markdown(
    "Spaced repetition reinforces leadership concepts at **1, 3, 7, and 14-day intervals**. "
    "Concepts from completed modules return here for periodic verification. "
    "A failed review flags the concept for immediate re-teaching."
)

learner_id = st.session_state.get("active_learner_id")
if not learner_id:
    st.warning("Please select or create a learner on the Home page.")
    st.stop()

learner = get_learner(learner_id)
queue = get_review_queue(learner_id)

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Total Due Today", f"{queue['total_due_today_count']} items")
with col2:
    st.metric("Overdue Items", f"{queue['total_overdue_count']} items", delta=f"{queue['total_overdue_count']} urgent" if queue['total_overdue_count'] > 0 else "None", delta_color="inverse")
with col3:
    st.metric("Upcoming in Queue", f"{len(queue['upcoming'])} items")

st.markdown("---")

active_items = queue["overdue"] + queue["due_today"]
if not active_items:
    st.success("🎉 **All caught up!** No concepts currently due for spaced review. Check back tomorrow or advance to new lessons.")
    if queue["upcoming"]:
        st.markdown("### Upcoming Scheduled Reviews")
        for up in queue["upcoming"]:
            st.markdown(f"- ⏳ **{up['concept_id'].replace('_', ' ').title()}** (Module: `{up['module_id']}`) — Due on `{up['due_date']}` (Interval: {up['interval_days']} days)")
else:
    st.markdown(f"### Review Queue ({len(active_items)} items requiring action)")
    
    # Render active review questions
    for idx, item in enumerate(active_items):
        is_overdue = item in queue["overdue"]
        badge = "🔴 OVERDUE" if is_overdue else "🔵 DUE TODAY"
        
        with st.container():
            st.markdown(
                f"""
                <div style="border: 1px solid {'#EF4444' if is_overdue else '#2563EB'}; border-radius: 8px; padding: 14px; margin-bottom: 16px;">
                    <span style="font-weight: bold; color: {'#EF4444' if is_overdue else '#2563EB'};">{badge}</span> | 
                    <strong>Concept:</strong> {item['concept_id'].replace('_', ' ').title()} | 
                    <strong>Current Interval:</strong> {item['interval_days']} Day(s)
                </div>
                """,
                unsafe_allow_html=True
            )
            
            # Review question form
            with st.form(f"review_form_{item['id']}"):
                st.markdown(f"**Question Scenario:** Reviewing core principles of *{item['concept_id'].replace('_', ' ').title()}*:")
                
                # Dynamic review question text
                st.markdown(
                    "As an incoming analytics leader, how do you explain the primary risk of using this pattern or metric "
                    "without governed checks to your executive committee?"
                )
                
                user_review_answer = st.radio(
                    "Select the sound executive approach:",
                    options=[
                        "Accept the output as long as the numbers look plausible and there are no syntax errors.",
                        "Enforce automated schema validation, pre-join row count assertions, and documented semantic layer definitions.",
                        "Delegate all metric validation entirely to external contractors without internal oversight."
                    ],
                    key=f"rev_opt_{item['id']}"
                )
                
                submit_rev = st.form_submit_button("Submit Review Response", type="primary")
                if submit_rev:
                    is_correct = (user_review_answer == "Enforce automated schema validation, pre-join row count assertions, and documented semantic layer definitions.")
                    score = 100.0 if is_correct else 40.0
                    
                    with st.spinner("Recording spaced repetition interval..."):
                        rec = record_review_result(item["id"], score, is_correct)
                        if is_correct:
                            if rec.get("status") == "mastered":
                                st.success("🏆 Concept Mastered! Completed full 14-day spaced retention cycle.")
                            else:
                                st.success(f"✅ Passed! Interval advanced to {rec.get('next_interval')} days. Next due: {rec.get('due_date')}")
                        else:
                            st.error(f"❌ Review missed. Interval reset to 1 day. Concept flagged for re-teaching.")
                        st.rerun()
