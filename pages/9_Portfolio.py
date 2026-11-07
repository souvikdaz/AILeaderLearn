import streamlit as st
from config.settings import load_track_config
from core.db import get_learner
from core.portfolio_builder import (
    generate_portfolio_markdown, export_portfolio_zip, get_learner_portfolio_items
)

st.title("💼 Executive Portfolio")
st.markdown(
    "Your portfolio curates your completed case studies, verified query audits, and architectural memos "
    "into an executive-ready package to present in senior interviews and board presentations."
)

learner_id = st.session_state.get("active_learner_id")
if not learner_id:
    st.warning("Please select or create a learner on the Home page.")
    st.stop()

learner = get_learner(learner_id)
items = get_learner_portfolio_items(learner_id)

col_d1, col_d2 = st.columns([3, 1])
with col_d1:
    st.markdown(f"**Leader:** `{learner['name']}` | **Target Role:** `{learner.get('target_level', 'Head of Analytics')}`")
    st.caption(f"Verified Portfolio Assets: {len(items)} items")

with col_d2:
    # ZIP export
    zip_bytes = export_portfolio_zip(learner_id)
    st.download_button(
        label="📦 Export Portfolio as ZIP",
        data=zip_bytes,
        file_name=f"portfolio_{learner_id}.zip",
        mime="application/zip",
        type="primary"
    )

st.markdown("---")

tab_preview, tab_assets = st.tabs(["Rendered Markdown Preview", "Individual Verified Assets"])

with tab_preview:
    portfolio_md = generate_portfolio_markdown(learner_id)
    st.markdown(portfolio_md)

with tab_assets:
    if not items:
        st.info("No verified assets yet. Complete labs and pass project briefs to populate your portfolio.")
    else:
        for idx, it in enumerate(items):
            icon = "📁" if it["type"] == "project_case_study" else "🧪"
            with st.expander(f"{icon} {it['title']} ({it.get('module_id', '')})"):
                if it["type"] == "project_case_study":
                    st.markdown(f"**Score:** `{it['score']}%` | **File:** `{it['file_name']}`")
                    st.markdown(f"**Executive Strength:** *{it['strength']}*")
                    st.markdown("**Executive Content Excerpt:**")
                    st.text(it.get("content_preview", ""))
                else:
                    st.markdown(f"**Execution:** `{it['execution_status']}`")
                    st.markdown("**Submitted Code:**")
                    st.code(it.get("code_submitted", ""))
                    st.markdown(f"**Defense:** *\"{it.get('explain_answer', '')}\"*")
