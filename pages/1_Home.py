import streamlit as st
import json
from datetime import datetime, date
from core.db import get_all_learners, get_learner, create_learner
from config.settings import load_track_config

st.title("👥 Learner Profiles & Setup")
st.markdown(
    "Welcome to **AI Leader Learn**. This accelerator transforms experienced reporting and MIS leaders "
    "into hands-on Data & AI leaders within 90 days. Manage multiple learner profiles below."
)

track = load_track_config()

tab_select, tab_create, tab_baseline = st.tabs(["Active Learners", "Create New Learner", "Baseline & Conceptual Bridge"])

with tab_select:
    learners = get_all_learners()
    if not learners:
        st.info("No learners created yet. Switch to the 'Create New Learner' tab to register your profile.")
    else:
        st.markdown(f"### Select Active Profile ({len(learners)} registered)")
        cols = st.columns(min(3, len(learners)))
        
        for idx, l in enumerate(learners):
            col = cols[idx % len(cols)]
            with col:
                is_active = (l["id"] == st.session_state.get("active_learner_id"))
                card_border = "border: 2px solid #2563EB;" if is_active else "border: 1px solid #E2E8F0;"
                st.markdown(
                    f"""
                    <div style="{card_border} padding: 16px; border-radius: 8px; margin-bottom: 12px; background: {'#F0F7FF' if is_active else '#FFFFFF'};">
                        <h4 style="margin: 0; color: #1E293B;">{l['name']} {'⭐ (Active)' if is_active else ''}</h4>
                        <p style="margin: 4px 0; color: #64748B; font-size: 0.9em;"><strong>Role:</strong> {l.get('current_role', 'Manager')}</p>
                        <p style="margin: 4px 0; color: #64748B; font-size: 0.9em;"><strong>Target:</strong> {l.get('target_level', 'Leader')}</p>
                        <p style="margin: 4px 0; color: #64748B; font-size: 0.9em;"><strong>Industry:</strong> {l.get('industry', 'Technology')}</p>
                        <p style="margin: 4px 0; color: #64748B; font-size: 0.9em;"><strong>Pace:</strong> {l.get('hours_per_week', 10)} hrs/week</p>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
                if not is_active:
                    if st.button(f"Switch to {l['name']}", key=f"btn_switch_{l['id']}"):
                        st.session_state["active_learner_id"] = l["id"]
                        st.rerun()

with tab_create:
    st.markdown("### Register New Learner Profile")
    st.caption("Customize your leadership track, target level, and committed study schedule.")
    
    with st.form("create_learner_form", clear_on_submit=False):
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            full_name = st.text_input("Full Name *", placeholder="e.g. Alex Chen")
            current_role = st.text_input("Current Role *", placeholder="e.g. Lead MIS Analyst / Senior Reporting Manager")
            years_exp = st.number_input("Years of Experience *", min_value=1, max_value=40, value=7)
            industry = st.selectbox(
                "Industry Domain",
                options=["Financial Services", "Retail & E-Commerce", "Healthcare", "Technology / SaaS", "Manufacturing & Supply Chain", "Telecommunications", "Other"]
            )
        with col_f2:
            target_role = st.selectbox(
                "Target Leadership Role *",
                options=track.get("target_roles", ["Head of Analytics", "AI Program Lead", "Director of Insights", "Analytics Manager"])
            )
            hours_per_week = st.slider("Target Weekly Commitment (Hours) *", min_value=5, max_value=30, value=10, step=1)
            start_date = st.date_input("Program Start Date *", value=date.today())
            tools = st.multiselect(
                "Tools You Regularly Use",
                options=["Microsoft Excel (Advanced)", "Power BI", "Tableau", "VBA / Macros", "Basic SQL", "Python / pandas", "Jupyter Notebooks", "Looker", "Alteryx"],
                default=["Microsoft Excel (Advanced)", "Power BI"]
            )
            
        submitted = st.form_submit_button("🚀 Create Profile & Start Diagnostic", type="primary")
        if submitted:
            if not full_name.strip() or not current_role.strip():
                st.error("Please fill in all required fields (Name and Current Role).")
            else:
                learner_id = full_name.lower().replace(" ", "_").strip()
                # Check collision
                if get_learner(learner_id):
                    learner_id = f"{learner_id}_{int(datetime.now().timestamp())}"
                    
                new_learner = create_learner(
                    learner_id=learner_id,
                    name=full_name.strip(),
                    track_id="data_ai_leadership",
                    current_role=current_role.strip(),
                    years_of_experience=int(years_exp),
                    target_level=target_role,
                    industry=industry,
                    tools_known=tools,
                    hours_per_week=int(hours_per_week),
                    start_date=start_date.isoformat()
                )
                st.session_state["active_learner_id"] = learner_id
                st.success(f"Profile created for **{full_name}**! Please proceed to the Placement Diagnostic.")
                st.rerun()

with tab_baseline:
    st.markdown("### Learner Baseline & Conceptual Mapping")
    baseline = track.get("learner_baseline", {})
    st.info(f"**Baseline Assumption:** {baseline.get('description', '')}")
    
    st.markdown("#### How Excel & Reporting Concepts Map to Analytics Leadership")
    bridges = baseline.get("conceptual_bridges", [])
    for b in bridges:
        with st.expander(f"📊 {b['excel_concept']} ➔ 🏛️ {b['leadership_concept']}", expanded=True):
            st.markdown(f"**Leadership Transformation:** {b['business_impact']}")
