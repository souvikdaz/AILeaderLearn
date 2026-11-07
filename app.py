import sys
from pathlib import Path

# Ensure repository root is always at the head of sys.path on Streamlit Cloud & local runs
ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Handle potential module hot-reloading on Streamlit Cloud
import importlib
try:
    import core.db
    if not hasattr(core.db, "record_learner_activity"):
        importlib.reload(core.db)
except Exception:
    pass

import streamlit as st
import json
from datetime import datetime
from config.settings import load_track_config, DB_PATH
from core.db import init_db, get_all_learners, get_learner, record_learner_activity
from core.progress_tracker import calculate_learner_metrics
from core.placement import has_completed_diagnostic, get_diagnostic_draft

# Streamlit Page Configuration
st.set_page_config(
    page_title="AI Leader Learn | Data & AI Leadership Accelerator",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize database on startup
@st.cache_resource
def bootstrap_database():
    init_db()
    return True

bootstrap_database()

# Cached track loader
@st.cache_data
def get_cached_track_config():
    return load_track_config()

track = get_cached_track_config()

# Initialize session state for authentication and active learner
if "logged_in" not in st.session_state:
    # If active_learner_id or admin_authenticated was pre-injected (e.g. tests), respect it
    if st.session_state.get("active_learner_id"):
        st.session_state["logged_in"] = True
        st.session_state["user_role"] = "learner"
    elif st.session_state.get("admin_authenticated"):
        st.session_state["logged_in"] = True
        st.session_state["user_role"] = "admin"
    else:
        st.session_state["logged_in"] = False
        st.session_state["user_role"] = None
        st.session_state["active_learner_id"] = None

if "user_role" not in st.session_state:
    if st.session_state.get("admin_authenticated"):
        st.session_state["user_role"] = "admin"
    elif st.session_state.get("active_learner_id"):
        st.session_state["user_role"] = "learner"
    else:
        st.session_state["user_role"] = None

if "active_learner_id" not in st.session_state:
    st.session_state["active_learner_id"] = None

if "admin_authenticated" not in st.session_state:
    st.session_state["admin_authenticated"] = (st.session_state.get("user_role") == "admin")

if "current_module_id" not in st.session_state:
    st.session_state["current_module_id"] = "module_1"

if "current_lesson_id" not in st.session_state:
    st.session_state["current_lesson_id"] = "m1_l1"

# Record learner activity if logged in as learner
if st.session_state.get("logged_in") and st.session_state.get("active_learner_id"):
    record_learner_activity(st.session_state["active_learner_id"])

# Render Persistent Global Sidebar
with st.sidebar:
    st.markdown("### 🎯 **AI Leader Learn**")
    st.caption("90-Day Executive Accelerator for Data & AI Leaders")
    st.markdown("---")
    
    if not st.session_state.get("logged_in"):
        st.info("🔐 **Sign In Required**\nPlease log in to your learner profile or authenticate as administrator to access your progress.")
        st.markdown("**Executive Transformation Pillars:**")
        st.markdown("- Relational SQL & Python Hygiene\n- Metric Trees & Executive Dashboards\n- RAG Architectures & LLM Evaluation\n- Leadership Interview Drills")
        st.markdown("---")
        st.caption("🔒 *All progress & submissions auto-saved to SQLite.*")
    elif st.session_state.get("user_role") == "admin":
        st.markdown("#### 🛡️ **Administrator Active**")
        st.caption("Global cohort telemetry & system management")
        st.markdown("---")
        if st.button("🚪 Log Out of Admin", key="sidebar_admin_logout_btn", use_container_width=True):
            st.session_state["logged_in"] = False
            st.session_state["user_role"] = None
            st.session_state["admin_authenticated"] = False
            st.session_state["active_learner_id"] = None
            st.rerun()
        st.markdown("---")
        st.caption("🔒 *Administrative console protected by environment key.*")
    else: # Logged in as Learner
        selected_id = st.session_state.get("active_learner_id")
        learner_info = get_learner(selected_id) if selected_id else None
        
        if learner_info:
            has_diag = has_completed_diagnostic(selected_id)
            st.markdown(f"👤 **{learner_info['name']}**")
            st.caption(f"{learner_info.get('current_role', 'Manager')} ➔ `{learner_info.get('target_level', 'Leader')}`")
            
            if not has_diag:
                st.warning("🧭 **Step 1: Diagnostic Required**\n\nComplete and submit your Placement Diagnostic to unlock your custom curriculum and dashboard.")
                drafts = get_diagnostic_draft(selected_id)
                saved_count = len(drafts)
                st.progress(saved_count / 22.0, text=f"Diagnostic: {saved_count}/22 saved")
                st.caption(f"Commitment: {learner_info.get('hours_per_week', 10)} hrs/week")
            else:
                metrics = calculate_learner_metrics(selected_id)
                
                # Find current phase
                passed_mods = metrics.get("passed_modules", 0)
                if passed_mods <= 4:
                    curr_phase = "Phase 1: Technical Literacy"
                elif passed_mods <= 8:
                    curr_phase = "Phase 2: Operating Models"
                elif passed_mods <= 12:
                    curr_phase = "Phase 3: AI in Practice"
                else:
                    curr_phase = "Phase 4: Executive Readiness"
                    
                st.markdown(f"**Phase:** *{curr_phase}*")
                
                col_sb1, col_sb2 = st.columns(2)
                with col_sb1:
                    st.metric("Days Left", f"{metrics.get('days_left', 90)}d")
                with col_sb2:
                    pace_lbl = metrics.get('pace_label', 'On Track')
                    if "Behind" in pace_lbl:
                        st.markdown(f"**Pace:** :red[{pace_lbl}]")
                    elif "Ahead" in pace_lbl:
                        st.markdown(f"**Pace:** :green[{pace_lbl}]")
                    else:
                        st.markdown(f"**Pace:** :blue[{pace_lbl}]")
                        
                st.caption(f"Commitment: {learner_info.get('hours_per_week', 10)} hrs/week")
                
            st.markdown("---")
            if st.button("🚪 Log Out", key="sidebar_learner_logout_btn", use_container_width=True):
                st.session_state["logged_in"] = False
                st.session_state["user_role"] = None
                st.session_state["active_learner_id"] = None
                st.rerun()
        else:
            st.warning("Learner profile not found.")
            if st.button("Return to Login", key="sidebar_return_login"):
                st.session_state["logged_in"] = False
                st.session_state["user_role"] = None
                st.session_state["active_learner_id"] = None
                st.rerun()
                
        st.markdown("---")
        st.markdown("🔒 *All progress & submissions auto-saved to SQLite.*")

# Configure Page Navigation with st.navigation based on authentication state
if not st.session_state.get("logged_in"):
    # Non-authenticated users only have access to Login & Profile creation
    pages = [
        st.Page("pages/1_Home.py", title="Sign In & Register", icon="🔐"),
    ]
elif st.session_state.get("user_role") == "admin":
    # Administrator view: Administration console first, with curriculum preview
    pages = {
        "Administration": [
            st.Page("pages/12_Admin.py", title="Administration Console", icon="⚙️"),
        ],
        "Learner Preview": [
            st.Page("pages/3_Dashboard.py", title="Executive Dashboard", icon="📊"),
            st.Page("pages/4_Learn.py", title="Learn & Tutor", icon="📖"),
            st.Page("pages/5_Lab.py", title="Hands-On Lab", icon="🧪"),
        ]
    }
else:
    active_lid = st.session_state.get("active_learner_id")
    has_diag = has_completed_diagnostic(active_lid)
    
    if not has_diag:
        # Mandatory Placement Diagnostic must be completed first before unlocking curriculum
        pages = {
            "Diagnostic Assessment": [
                st.Page("pages/2_Placement.py", title="Placement Diagnostic", icon="🧭", default=True),
            ],
            "Account": [
                st.Page("pages/1_Home.py", title="My Profile", icon="👤"),
            ]
        }
    else:
        # Logged in Learner: Full 90-day accelerator curriculum, labs, portfolio & career
        pages = {
            "Curriculum & Practice": [
                st.Page("pages/3_Dashboard.py", title="Executive Dashboard", icon="📊", default=True),
                st.Page("pages/4_Learn.py", title="Learn & Tutor", icon="📖"),
                st.Page("pages/5_Lab.py", title="Hands-On Lab", icon="🧪"),
                st.Page("pages/6_Quiz.py", title="Spaced Review Quiz", icon="🔁"),
                st.Page("pages/7_Mastery.py", title="Mastery Gate", icon="🏆"),
            ],
            "Portfolio & Career": [
                st.Page("pages/8_Projects.py", title="Projects & Submissions", icon="📁"),
                st.Page("pages/9_Portfolio.py", title="Executive Portfolio", icon="💼"),
                st.Page("pages/10_Mock_Interview.py", title="Mock Interview Drill", icon="🎙️"),
                st.Page("pages/11_Career_Readiness.py", title="Career Readiness", icon="🚀"),
            ],
            "Learner Setup": [
                st.Page("pages/2_Placement.py", title="Placement Diagnostic", icon="🧭"),
                st.Page("pages/1_Home.py", title="My Profile", icon="👤"),
            ]
        }

pg = st.navigation(pages)
pg.run()
