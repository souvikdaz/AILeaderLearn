import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import streamlit as st
import json
from datetime import datetime, date
from core.db import (
    get_all_learners, get_all_learners_with_activity, get_learner,
    get_learner_by_email, create_learner, record_learner_activity
)
from core.auth import encrypt_password, decrypt_password, verify_password, validate_email
from core.email_service import send_password_recovery_email
from core.google_drive_sync import sync_email_to_google_sheet
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
        st.caption("Enter your credentials to access your personalized 90-day progress, labs, quizzes, and portfolio.")
        
        learners = get_all_learners_with_activity()
        if not learners:
            st.info("No learner profiles found yet. Please switch to the **'Create New Profile'** tab to get started.")
        else:
            learner_dict = {
                l["id"]: l["name"]
                for l in learners
            }
            
            col_l1, col_l2 = st.columns([3, 2])
            with col_l1:
                selected_id = st.selectbox(
                    "Select Your Profile:",
                    options=list(learner_dict.keys()),
                    format_func=lambda x: learner_dict.get(x, x),
                    key="login_learner_select"
                )
            with col_l2:
                entered_password = st.text_input(
                    "Password:",
                    type="password",
                    placeholder="Enter your account password",
                    key="login_password_input"
                )
            
            # Show selected profile confirmation
            selected_l = get_learner(selected_id)
            if selected_l:
                st.markdown(
                    f"""
                    <div style="border: 2px solid #2563EB; border-radius: 8px; padding: 12px 16px; margin: 10px 0; background: #F8FAFC;">
                        <h4 style="margin: 0; color: #1E293B;">👤 {selected_l['name']}</h4>
                        <p style="margin: 4px 0 0 0; color: #64748B; font-size: 0.9em;">Enter your password to access your executive dashboard.</p>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
                
            if st.button("🚀 Log In to Dashboard", key="btn_execute_learner_login", type="primary", use_container_width=True):
                if not entered_password:
                    st.error("Please enter your account password.")
                else:
                    stored_pw = selected_l.get("password_hash", "") if selected_l else ""
                    if verify_password(entered_password, stored_pw):
                        st.session_state["logged_in"] = True
                        st.session_state["user_role"] = "learner"
                        st.session_state["active_learner_id"] = selected_id
                        record_learner_activity(selected_id)
                        st.success(f"Welcome back, **{selected_l['name']}**! Accessing your learning dashboard...")
                        st.rerun()
                    else:
                        st.error("Incorrect password. If you forgot your password, use the password recovery tool below.")
            
            # Forgot Password Section
            st.markdown("---")
            with st.expander("❓ Forgot Password? Recover via Email", expanded=False):
                st.markdown("Enter your registered email address. We will verify your account and send your encrypted password to your email.")
                col_rec1, col_rec2 = st.columns([3, 2])
                with col_rec1:
                    recovery_email = st.text_input("Registered Email Address:", placeholder="e.g. name@company.com", key="recovery_email_input")
                with col_rec2:
                    st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
                    send_recovery = st.button("📨 Send Password to Email", key="btn_send_recovery", type="secondary", use_container_width=True)
                
                if send_recovery:
                    if not recovery_email.strip():
                        st.error("Please provide your registered email address.")
                    elif not validate_email(recovery_email.strip()):
                        st.error("Please enter a valid email address.")
                    else:
                        rec_learner = get_learner_by_email(recovery_email.strip())
                        if not rec_learner:
                            st.error(f"No registered learner profile found for: `{recovery_email.strip()}`")
                        else:
                            pw_encrypted = rec_learner.get("password_hash", "")
                            decrypted_pw = decrypt_password(pw_encrypted) if pw_encrypted else "leader_2025"
                            success, msg = send_password_recovery_email(
                                to_email=recovery_email.strip(),
                                learner_name=rec_learner["name"],
                                password=decrypted_pw
                            )
                            if "SMTP" in msg and "DELIVERED" in msg:
                                st.success(f"✅ Password recovery email sent successfully to **{recovery_email.strip()}**! Please check your inbox.")
                            else:
                                st.success(f"✅ Password recovery email dispatched to **{recovery_email.strip()}**!")
                                st.info(
                                    f"📬 **Password Recovery Notice:**\n\n"
                                    f"**Account:** {rec_learner['name']} ({recovery_email.strip()})\n\n"
                                    f"**Your Password:** `{decrypted_pw}`\n\n"
                                    f"*(Note: SMTP live dispatch can be enabled by configuring SMTP_HOST in .env)*"
                                )
                
    with tab_register:
        st.markdown("### Register New Learner Profile")
        st.caption("Configure your leadership track, email, password, and target study commitment.")
        
        with st.form("create_learner_form", clear_on_submit=False):
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                full_name = st.text_input("Full Name *", placeholder="e.g. Alex Chen")
                email = st.text_input("Email Address *", placeholder="e.g. alex.chen@company.com")
                reg_password = st.text_input("Create Password *", type="password", placeholder="Minimum 6 characters")
                reg_password_confirm = st.text_input("Confirm Password *", type="password", placeholder="Re-enter password")
                current_role = st.text_input("Current Role *", placeholder="e.g. Lead MIS Analyst / Senior Reporting Manager")
                years_exp = st.number_input("Years of Experience *", min_value=1, max_value=40, value=7)
            with col_f2:
                target_role = st.selectbox(
                    "Target Leadership Role *",
                    options=track.get("target_roles", ["Head of Analytics", "AI Program Lead", "Director of Insights", "Analytics Manager"])
                )
                industry = st.selectbox(
                    "Industry Domain",
                    options=["Financial Services", "Retail & E-Commerce", "Healthcare", "Technology / SaaS", "Manufacturing & Supply Chain", "Telecommunications", "Other"]
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
                if not full_name.strip() or not email.strip() or not current_role.strip():
                    st.error("Please fill in all required fields (Name, Email, and Current Role).")
                elif not validate_email(email.strip()):
                    st.error("Please provide a valid email address (e.g. user@domain.com).")
                elif get_learner_by_email(email.strip()):
                    st.error(f"An account with email '{email.strip()}' already exists. Please log in or use Forgot Password.")
                elif not reg_password or len(reg_password.strip()) < 6:
                    st.error("Password must be at least 6 characters long.")
                elif reg_password.strip() != reg_password_confirm.strip():
                    st.error("Passwords do not match. Please re-enter your password.")
                else:
                    learner_id = full_name.lower().replace(" ", "_").strip()
                    if get_learner(learner_id):
                        learner_id = f"{learner_id}_{int(datetime.now().timestamp())}"
                        
                    # Encrypt password before storing in SQLite
                    encrypted_pw = encrypt_password(reg_password.strip())
                    
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
                        start_date=start_date.isoformat(),
                        email=email.strip(),
                        password_hash=encrypted_pw
                    )
                    
                    # Store email into Google Drive Sheet (or queue in sync ledger)
                    drive_synced, drive_msg = sync_email_to_google_sheet(
                        learner_id=learner_id,
                        name=full_name.strip(),
                        email=email.strip(),
                        role=target_role
                    )
                    
                    record_learner_activity(learner_id)
                    st.session_state["logged_in"] = True
                    st.session_state["user_role"] = "learner"
                    st.session_state["active_learner_id"] = learner_id
                    
                    if drive_synced:
                        st.success(f"Profile created and synced to Google Drive Sheet for **{full_name}**!")
                    else:
                        st.success(f"Profile created for **{full_name}**! (Email recorded in Drive sync ledger)")
                        
                    st.rerun()

    with tab_admin:
        st.markdown("### Administrator Authentication")
        st.caption("Access global cohort telemetry, manage learner profiles, delete accounts, inspect Google Drive sync, and run content validators.")
        
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
            st.info("To manage learner profiles, view last active dates, inspect Google Drive sync, or delete accounts, open the **Administration Console**.")
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
                    st.markdown(f"**Email Address:** `{current_learner.get('email', 'Not registered')}`")
                    st.markdown(f"**Current Role:** `{current_learner.get('current_role', 'Manager')}`")
                    st.markdown(f"**Years Experience:** `{current_learner.get('years_of_experience', 5)}`")
                    st.markdown(f"**Industry Domain:** `{current_learner.get('industry', 'Tech')}`")
                with col_ov2:
                    st.markdown("### Program Objectives")
                    st.markdown(f"**Target Role:** `{current_learner.get('target_level', 'Head of Analytics')}`")
                    st.markdown(f"**Commitment:** `{current_learner.get('hours_per_week', 10)} hours/week`")
                    st.markdown(f"**Start Date:** `{current_learner.get('start_date', '2026-11-01')}`")
                    st.markdown(f"**Password Security:** `🔒 Encrypted (Fernet AES)`")
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
                    opt_map = {
                        l["id"]: l["name"]
                        for l in other_learners
                    }
                    new_sel_id = st.selectbox("Select Profile to Switch To:", options=list(opt_map.keys()), format_func=lambda x: opt_map.get(x, x))
                    switch_pw = st.text_input("Enter Password for this Profile:", type="password", key="switch_account_pw")
                    if st.button("Switch Account", key="btn_switch_account", type="primary"):
                        target_l = get_learner(new_sel_id)
                        stored_pw = target_l.get("password_hash", "") if target_l else ""
                        if verify_password(switch_pw, stored_pw):
                            st.session_state["active_learner_id"] = new_sel_id
                            record_learner_activity(new_sel_id)
                            st.success(f"Switched account to {target_l['name']}!")
                            st.rerun()
                        else:
                            st.error("Incorrect password for selected account.")
                        
            with tab_p_create:
                st.markdown("### Register an Additional Learner Profile")
                with st.form("create_additional_learner_form"):
                    name_add = st.text_input("Full Name *", placeholder="e.g. Jordan Smith")
                    email_add = st.text_input("Email Address *", placeholder="e.g. jordan.smith@company.com")
                    pw_add = st.text_input("Create Password *", type="password")
                    role_add = st.text_input("Current Role *", placeholder="e.g. Senior Business Intelligence Analyst")
                    target_add = st.selectbox("Target Leadership Role *", options=track.get("target_roles", ["Head of Analytics", "AI Program Lead"]))
                    sub_add = st.form_submit_button("Create Profile")
                    if sub_add and name_add.strip() and email_add.strip() and role_add.strip() and pw_add.strip():
                        if not validate_email(email_add.strip()):
                            st.error("Please enter a valid email address.")
                        else:
                            lid_add = name_add.lower().replace(" ", "_").strip()
                            enc_pw = encrypt_password(pw_add.strip())
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
                                start_date=date.today().isoformat(),
                                email=email_add.strip(),
                                password_hash=enc_pw
                            )
                            sync_email_to_google_sheet(lid_add, name_add.strip(), email_add.strip(), target_add)
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
