import streamlit as st
import pandas as pd
from config.settings import ADMIN_PASSWORD, load_track_config
from core.db import get_all_learners, execute_query
from core.content_validator import validate_all_content
from core.mastery_gate import reset_module
from core.progress_tracker import generate_misconception_heatmap

st.title("⚙️ Administrative Console")
st.markdown("Content validation, global learner telemetry, module resets, and execution audit logs.")

# Password authentication
if "admin_authenticated" not in st.session_state:
    st.session_state["admin_authenticated"] = False

if not st.session_state["admin_authenticated"]:
    with st.form("admin_auth_form"):
        pwd = st.text_input("Enter Admin Password:", type="password")
        sub_pwd = st.form_submit_button("Authenticate", type="primary")
        if sub_pwd:
            if pwd == ADMIN_PASSWORD:
                st.session_state["admin_authenticated"] = True
                st.success("Authenticated successfully!")
                st.rerun()
            else:
                st.error("Invalid administrator password.")
    st.stop()

# Admin is authenticated
st.success("🔒 Administrator Session Active")
if st.button("Log Out of Admin"):
    st.session_state["admin_authenticated"] = False
    st.rerun()

st.markdown("---")

tab_val, tab_learners, tab_labs, tab_heat = st.tabs([
    "Curriculum Content Validator", "All Learners & Progress", "Lab Execution Logs", "Global Misconception Heatmap"
])

with tab_val:
    st.markdown("### 🧪 Automated Curriculum Content Validator")
    st.caption("Verifies that every module has complete labs, rubrics, term definitions, concise sentences, and working test queries.")
    
    if st.button("Run Content Validator Now", type="primary"):
        with st.spinner("Validating content structure, YAML files, and test executions..."):
            val_res = validate_all_content()
            
            if val_res["passed"]:
                st.success(f"✅ Content Validation Passed! Validated {val_res['modules_validated']} Phase 1 modules and Phase 2-4 outlines.")
            else:
                st.error(f"❌ Content Validation Failed with {val_res['error_count']} errors.")
                for err in val_res["errors"]:
                    st.markdown(f"- 🔴 `{err}`")
                    
            if val_res["warning_count"] > 0:
                with st.expander(f"⚠️ Editorial Warnings ({val_res['warning_count']} items)", expanded=False):
                    for w in val_res["warnings"]:
                        st.markdown(f"- 🟡 {w}")

with tab_learners:
    st.markdown("### 👥 Global Learners Progress Matrix")
    learners = get_all_learners()
    
    if not learners:
        st.info("No learners registered.")
    else:
        df_learners = pd.DataFrame(learners)
        st.dataframe(df_learners[["id", "name", "current_role", "target_level", "industry", "hours_per_week", "start_date", "status"]], use_container_width=True)
        
        st.markdown("#### Manage Learner Module Resets")
        st.caption("Modules can be reset if the learner has reached 3 failed attempts (or forced by admin).")
        
        col_res1, col_res2, col_res3 = st.columns(3)
        with col_res1:
            res_learner_id = st.selectbox("Select Learner:", options=[l["id"] for l in learners], key="admin_res_learner")
        with col_res2:
            res_module_id = st.selectbox("Select Module to Reset:", options=["module_1", "module_2", "module_3", "module_4"], key="admin_res_mod")
        with col_res3:
            st.markdown("<div style='height:28px;'></div>", unsafe_allow_html=True)
            if st.button("🔄 Execute Reset", key="btn_exec_reset"):
                success = reset_module(res_learner_id, res_module_id, force=True)
                if success:
                    st.success(f"Module '{res_module_id}' has been reset for {res_learner_id}!")
                else:
                    st.error("Reset failed: reset conditions not met.")

with tab_labs:
    st.markdown("### 🔍 Sandbox Lab Execution Logs")
    sql_labs = """
    SELECT id, learner_id, module_id, lab_id, execution_status, explain_line_passed, attempt_number, created_at, code_submitted
    FROM lab_attempts
    ORDER BY id DESC LIMIT 20
    """
    rows = execute_query(sql_labs)
    if rows:
        df_l = pd.DataFrame([dict(r) for r in rows])
        st.dataframe(df_l[["id", "learner_id", "lab_id", "execution_status", "explain_line_passed", "attempt_number", "created_at"]], use_container_width=True)
        with st.expander("Inspect Raw Submitted Code Samples"):
            for r in rows[:5]:
                st.markdown(f"**ID {r['id']} ({r['learner_id']} - {r['lab_id']}):**")
                st.code(r["code_submitted"])
    else:
        st.caption("No lab execution logs found.")

with tab_heat:
    st.markdown("### 🌐 Global Cohort Misconception Heatmap")
    st.caption("Aggregates common student misconceptions across the entire learner cohort to guide curriculum updates.")
    fig_global_heat = generate_misconception_heatmap(learner_id=None)
    st.plotly_chart(fig_global_heat, use_container_width=True)
