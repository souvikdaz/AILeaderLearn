import streamlit as st
import json
from datetime import datetime
from pathlib import Path
from config.settings import load_track_config, DB_PATH
from core.db import init_db, get_all_learners, get_learner
from core.progress_tracker import calculate_learner_metrics

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

# Initialize session state for learner and navigation state
if "active_learner_id" not in st.session_state:
    learners = get_all_learners()
    if learners:
        st.session_state["active_learner_id"] = learners[0]["id"]
    else:
        st.session_state["active_learner_id"] = None

if "current_module_id" not in st.session_state:
    st.session_state["current_module_id"] = "module_1"

if "current_lesson_id" not in st.session_state:
    st.session_state["current_lesson_id"] = "m1_l1"

# Render Persistent Global Sidebar
with st.sidebar:
    st.markdown("### 🎯 **AI Leader Learn**")
    st.caption("90-Day Executive Accelerator for Data & AI Leaders")
    st.markdown("---")
    
    learners = get_all_learners()
    learner_options = {l["id"]: f"{l['name']} ({l.get('target_level', 'Leader')})" for l in learners}
    
    if learner_options:
        current_idx = list(learner_options.keys()).index(st.session_state["active_learner_id"]) if st.session_state["active_learner_id"] in learner_options else 0
        selected_id = st.selectbox(
            "👤 **Select Active Learner**",
            options=list(learner_options.keys()),
            format_func=lambda x: learner_options.get(x, x),
            index=current_idx,
            key="sidebar_learner_selector"
        )
        if selected_id != st.session_state["active_learner_id"]:
            st.session_state["active_learner_id"] = selected_id
            st.rerun()
            
        # Display Learner Profile Summary Card
        learner_info = get_learner(selected_id)
        if learner_info:
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
                
            st.markdown(f"**Current Role:** {learner_info.get('current_role', 'Manager')}")
            st.markdown(f"**Target:** `{learner_info.get('target_level', 'Head of Analytics')}`")
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
                    
            st.caption(f"Target Commitment: {learner_info.get('hours_per_week', 10)} hrs/week")
    else:
        st.warning("No learner profile active. Create a learner on the Home page.")
        
    st.markdown("---")
    st.markdown("🔒 *All progress & submissions auto-saved to SQLite.*")

# Configure Page Navigation with st.navigation
pages = {
    "Learner Setup": [
        st.Page("pages/1_Home.py", title="Home / Learners", icon="👥"),
        st.Page("pages/2_Placement.py", title="Placement Diagnostic", icon="🧭"),
    ],
    "Curriculum & Practice": [
        st.Page("pages/3_Dashboard.py", title="Executive Dashboard", icon="📊"),
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
    "Management": [
        st.Page("pages/12_Admin.py", title="Administration", icon="⚙️"),
    ]
}

pg = st.navigation(pages)
pg.run()
