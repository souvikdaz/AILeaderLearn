import streamlit as st
import json
from datetime import datetime, date
from core.db import (
    get_all_learners, get_all_learners_with_activity, get_learner,
    create_learner, record_learner_activity
)
from config.settings import ADMIN_PASSWORD, load_track_config

track = load_track_config()

# Check authentication state
is_logged_in = st.session_state.get("logged_in", False)
user_role = st.session_state.get("user_role")
active_learner_id = st.session_state.get("active_learner_id")

if not is_logged_in:
    # LANDING & LOGIN PORTAL VIEW
    st.title("🎯 AI Leader Learn | Sign In & Profile Portal")
    st.markdown(
        "Welcome to the **90-Day Executive Accelerator for Data & AI Leaders**. "
        "Transform from recurring spreadsheet and MIS reporting into hands-on data & AI leadership."
    )
    
    tab_login, tab_register, tab_admin, tab_bridge = st.tabs([
        "🔑 Learner Log In", "✨ Create New Profile", "🛡️ Administrator Access", "📊 Baseline & Conceptual Bridge"
    ])
    
    with tab_login:
        st.markdown("### Log In to Your Learner Account")
        st.caption("Access your personalized 90-day progress, labs, quizzes, and portfolio.")
        
        learners = get_all_learners_with_activity()
        if not learners:
            st.info("No learner profiles found yet. Please switch to the **'Create New Profile'** tab to get started.")
        else:
            learner_dict = {
                l["id"]: f"{l['name']} — {l.get('current_role', 'Manager')} (Target: {l.get('target_level', 'Leader')})"
                for l in learners
            }
            
            selected_id = st.selectbox(
                "Select Your Profile:",
                options=list(learner_dict.keys()),
                format_func=lambda x: learner_dict.get(x, x),
                key="login_learner_select"
            )
            
            # Show preview card of selected profile
            selected_l = get_learner(selected_id)
            if selected_l:
                # Find matching activity record
                act_record = next((item for item in learners if item["id"] == selected_id), {})
                last_act = act_record.get("last_active_date", "Never")
                passed_mods = act_record.get("passed_modules", 0)
                
                st.markdown(
                    f"""
                    <div style="border: 2px solid #2563EB; border-radius: 8px; padding: 18px; margin: 16px 0; background: #F8FAFC;">
                        <h3 style="margin: 0; color: #1E293B;">👤 {selected_l['name']}</h3>
                        <p style="margin: 6px 0; color: #475569;"><strong>Current Role:</strong> {selected_l.get('current_role', 'Manager')} | <strong>Industry:</strong> {selected_l.get('industry', 'Tech')}</p>
                        <p style="margin: 4px 0; color: #475569;"><strong>Target Leadership Role:</strong> <code style="color: #2563EB;">{selected_l.get('target_level', 'Head of Analytics')}</code></p>
                        <p style="margin: 4px 0; color: #64748B; font-size: 0.9em;"><strong>Weekly Commitment:</strong> {selected_l.get('hours_per_week', 10)} hrs/week | <strong>Passed Modules:</strong> {passed_mods} / 12</p>
                        <p style="margin: 4px 0; color: #0284C7; font-size: 0.9em;"><strong>Last Active Date:</strong> {last_act}</p>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
                
            if st.button("🚀 Log In to Dashboard", key="btn_execute_learner_login", type="primary", use_container_width=True):
                st.session_state["logged_in"] = True
                st.session_state["user_role"] = "learner"
                st.session_state["active_learner_id"] = selected_id
                record_learner_activity(selected_id)
                st.success(f"Welcome back, **{selected_l['name']}**! Accessing your learning dashboard...")
                st.rerun()
                
    with tab_register:
        st.markdown("### Register New Learner Profile")
        st.caption("Configure your leadership track, target level, and committed study schedule.")
        
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
                
            submitted = st.form_submit_button("🚀 Create Profile & Log In", type="primary", use_container_width=True)
            if submitted:
                if not full_name.strip() or not current_role.strip():
                    st.error("Please fill in all required fields (Full Name and Current Role).")
                else:
                    learner_id = full_name.lower().replace(" ", "_").strip()
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
                    record_learner_activity(learner_id)
                    st.session_state["logged_in"] = True
                    st.session_state["user_role"] = "learner"
                    st.session_state["active_learner_id"] = learner_id
                    st.success(f"Profile created for **{full_name}**! Redirecting to Placement Diagnostic...")
                    st.rerun()

    with tab_admin:
        st.markdown("### Administrator Authentication")
        st.caption("Access global cohort telemetry, manage learner profiles, delete accounts, and run content validators.")
        
        with st.form("admin_login_portal_form"):
            admin_pwd = st.text_input("Enter Administrator Password:", type="password", placeholder="Enter admin password from .env")
            submit_admin = st.form_submit_button("🔐 Authenticate as Administrator", type="primary", use_container_width=True)
            if submit_admin:
                if admin_pwd == ADMIN_PASSWORD:
                    st.session_state["logged_in"] = True
                    st.session_state["user_role"] = "admin"
                    st.session_state["admin_authenticated"] = True
                    st.session_state["active_learner_id"] = None
                    st.success("Administrator authentication verified! Redirecting to Administration Console...")
                    st.rerun()
                else:
                    st.error("Invalid administrator password. Please verify ADMIN_PASSWORD in your .env configuration.")

    with tab_bridge:
        st.markdown("### Learner Baseline & Conceptual Mapping")
        baseline = track.get("learner_baseline", {})
        st.info(f"**Baseline Assumption:** {baseline.get('description', '')}")
        
        st.markdown("#### How Excel & Reporting Concepts Map to Analytics Leadership")
        bridges = baseline.get("conceptual_bridges", [])
        for b in bridges:
            with st.expander(f"📊 {b['excel_concept']} ➔ 🏛️ {b['leadership_concept']}", expanded=True):
                st.markdown(f"**Leadership Transformation:** {b['business_impact']}")

else:
    # LOGGED IN VIEW: PROFILE & SETTINGS
    active_id = st.session_state.get("active_learner_id")
    current_learner = get_learner(active_id) if active_id else None
    
    if user_role == "admin":
        st.title("⚙️ Administrator Profile")
        st.success("🔒 **Administrator Session Active**")
        st.markdown("You are currently logged in with administrative privileges.")
        col_ad1, col_ad2 = st.columns(2)
        with col_ad1:
            st.info("To manage learner profiles, view last active dates, or delete accounts, open the **Administration Console**.")
        with col_ad2:
            if st.button("🚪 Log Out of Administrator Session", key="btn_admin_self_logout", type="primary"):
                st.session_state["logged_in"] = False
                st.session_state["user_role"] = None
                st.session_state["admin_authenticated"] = False
                st.rerun()
    else:
        # Learner Profile View
        st.title("👤 My Learner Profile")
        if current_learner:
            record_learner_activity(active_id)
            st.markdown(f"Welcome back, **{current_learner['name']}**! Manage your active profile settings below.")
            
            tab_p_overview, tab_p_switch, tab_p_create, tab_p_bridge = st.tabs([
                "Profile Overview", "Switch Profile", "Register Another Learner", "Baseline & Conceptual Bridge"
            ])
            
            with tab_p_overview:
                col_ov1, col_ov2 = st.columns(2)
                with col_ov1:
                    st.markdown("### Profile Attributes")
                    st.markdown(f"**Full Name:** `{current_learner['name']}`")
                    st.markdown(f"**Current Role:** `{current_learner.get('current_role', 'Manager')}`")
                    st.markdown(f"**Years Experience:** `{current_learner.get('years_of_experience', 5)}`")
                    st.markdown(f"**Industry Domain:** `{current_learner.get('industry', 'Tech')}`")
                with col_ov2:
                    st.markdown("### Program Objectives")
                    st.markdown(f"**Target Role:** `{current_learner.get('target_level', 'Head of Analytics')}`")
                    st.markdown(f"**Commitment:** `{current_learner.get('hours_per_week', 10)} hours/week`")
                    st.markdown(f"**Start Date:** `{current_learner.get('start_date', '2026-11-01')}`")
                    st.markdown(f"**Last Active:** `{current_learner.get('last_active_at', 'Just now')}`")
                    
                st.markdown("---")
                if st.button("🚪 Log Out of Profile", key="btn_learner_self_logout", type="secondary"):
                    st.session_state["logged_in"] = False
                    st.session_state["user_role"] = None
                    st.session_state["active_learner_id"] = None
                    st.rerun()
                    
            with tab_p_switch:
                st.markdown("### Switch Active Learner Profile")
                learners = get_all_learners_with_activity()
                other_learners = [l for l in learners if l["id"] != active_id]
                if not other_learners:
                    st.info("No other learner profiles registered.")
                else:
                    opt_map = {l["id"]: f"{l['name']} ({l.get('target_level', 'Leader')}) - Last Active: {l.get('last_active_date', 'Never')}" for l in other_learners}
                    new_sel_id = st.selectbox("Select Profile to Switch To:", options=list(opt_map.keys()), format_func=lambda x: opt_map.get(x, x))
                    if st.button("Switch Account", key="btn_switch_account", type="primary"):
                        st.session_state["active_learner_id"] = new_sel_id
                        record_learner_activity(new_sel_id)
                        st.rerun()
                        
            with tab_p_create:
                st.markdown("### Register an Additional Learner Profile")
                with st.form("create_additional_learner_form"):
                    name_add = st.text_input("Full Name *", placeholder="e.g. Jordan Smith")
                    role_add = st.text_input("Current Role *", placeholder="e.g. Senior Business Intelligence Analyst")
                    target_add = st.selectbox("Target Leadership Role *", options=track.get("target_roles", ["Head of Analytics", "AI Program Lead"]))
                    sub_add = st.form_submit_button("Create Profile")
                    if sub_add and name_add.strip() and role_add.strip():
                        lid_add = name_add.lower().replace(" ", "_").strip()
                        create_learner(
                            learner_id=lid_add,
                            name=name_add.strip(),
                            track_id="data_ai_leadership",
                            current_role=role_add.strip(),
                            years_of_experience=5,
                            target_level=target_add,
                            industry="Technology",
                            tools_known=["Excel", "Power BI"],
                            hours_per_week=10,
                            start_date=date.today().isoformat()
                        )
                        st.session_state["active_learner_id"] = lid_add
                        st.success(f"Created and switched to {name_add}!")
                        st.rerun()
                        
            with tab_p_bridge:
                baseline = track.get("learner_baseline", {})
                st.info(f"**Baseline:** {baseline.get('description', '')}")
                bridges = baseline.get("conceptual_bridges", [])
                for b in bridges:
                    with st.expander(f"📊 {b['excel_concept']} ➔ 🏛️ {b['leadership_concept']}", expanded=False):
                        st.markdown(f"**Leadership Transformation:** {b['business_impact']}")
        else:
            st.warning("Active learner profile was not found in the database.")
            if st.button("Return to Login Portal"):
                st.session_state["logged_in"] = False
                st.session_state["active_learner_id"] = None
                st.rerun()
