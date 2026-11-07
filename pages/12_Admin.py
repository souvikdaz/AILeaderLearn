import streamlit as st
import pandas as pd
from config.settings import ADMIN_PASSWORD, load_track_config
from core.db import (
    get_all_learners, get_all_learners_with_activity, get_learner,
    delete_learner, execute_query
)
from core.content_validator import validate_all_content
from core.mastery_gate import reset_module
from core.progress_tracker import generate_misconception_heatmap

st.title("⚙️ Administrative Console")
st.markdown("Content validation, global learner telemetry, profile management, and execution audit logs.")

# Password authentication check
if not st.session_state.get("admin_authenticated") and st.session_state.get("user_role") != "admin":
    with st.form("admin_auth_form"):
        pwd = st.text_input("Enter Admin Password:", type="password")
        sub_pwd = st.form_submit_button("Authenticate", type="primary")
        if sub_pwd:
            if pwd == ADMIN_PASSWORD:
                st.session_state["admin_authenticated"] = True
                st.session_state["logged_in"] = True
                st.session_state["user_role"] = "admin"
                st.success("Authenticated successfully!")
                st.rerun()
            else:
                st.error("Invalid administrator password.")
    st.stop()

# Admin session header and logout
col_hdr1, col_hdr2 = st.columns([4, 1])
with col_hdr1:
    st.success("🔒 **Administrator Session Active** — Global Governance & Learner Management")
with col_hdr2:
    if st.button("🚪 Log Out of Admin", key="admin_page_logout_btn", use_container_width=True):
        st.session_state["admin_authenticated"] = False
        st.session_state["logged_in"] = False
        st.session_state["user_role"] = None
        st.rerun()

st.markdown("---")

# Navigation Tabs: Primary view is "Manage Learner Profiles"
tab_learners, tab_val, tab_labs, tab_heat = st.tabs([
    "Manage Learner Profiles", "Curriculum Content Validator", "Lab Execution Logs", "Global Misconception Heatmap"
])

with tab_learners:
    st.markdown("### 👥 Manage Learner Profiles")
    st.caption("Inspect learner telemetry, view last active timestamps, delete profiles, or execute module resets.")
    
    learners = get_all_learners_with_activity()
    if not learners:
        st.info("No learner profiles found in database.")
    else:
        # Build clean DataFrame with explicit Last Active Date
        table_data = []
        for l in learners:
            table_data.append({
                "Learner ID": l["id"],
                "Name": l["name"],
                "Current Role": l.get("current_role", "-"),
                "Target Leadership Level": l.get("target_level", "-"),
                "Industry": l.get("industry", "-"),
                "Hours/Wk": l.get("hours_per_week", 10),
                "Start Date": l.get("start_date", "-"),
                "Last Active Date": l.get("last_active_date", "Never"),
                "Passed Modules": f"{l.get('passed_modules', 0)} / 12",
                "Status": l.get("status", "active")
            })
            
        df_profiles = pd.DataFrame(table_data)
        st.dataframe(df_profiles, use_container_width=True, hide_index=True)
        
        st.markdown("---")
        st.markdown("#### 🛠️ Profile Management Actions")
        
        learner_ids = [l["id"] for l in learners]
        learner_map = {
            l["id"]: f"{l['name']} ({l['id']}) — Last Active: {l.get('last_active_date', 'Never')}"
            for l in learners
        }
        
        col_act1, col_act2 = st.columns(2)
        
        # 1. Delete Profile Section
        with col_act1:
            st.markdown("##### 🗑️ Delete Learner Profile")
            st.caption("Permanently purge a learner's account and all associated submissions and attempts.")
            
            del_learner_id = st.selectbox(
                "Select Profile to Delete:",
                options=learner_ids,
                format_func=lambda x: learner_map.get(x, x),
                key="admin_del_learner_select"
            )
            del_learner = get_learner(del_learner_id)
            
            if del_learner:
                st.warning(
                    f"⚠️ **Destructive Action:** Deleting **{del_learner['name']}** will permanently erase "
                    "all diagnostic scores, module progress, lab attempt code, rubric submissions, "
                    "mastery attempts, spaced review items, and mock interview drills."
                )
                confirm_del = st.checkbox(
                    f"I confirm permanent deletion of profile '{del_learner['name']}' ({del_learner_id})",
                    key="confirm_delete_checkbox"
                )
                if st.button("🗑️ Permanently Delete Profile", key="btn_exec_delete_profile", type="primary", disabled=not confirm_del):
                    delete_learner(del_learner_id)
                    if st.session_state.get("active_learner_id") == del_learner_id:
                        st.session_state["active_learner_id"] = None
                    st.success(f"Learner profile '{del_learner['name']}' ({del_learner_id}) has been permanently deleted.")
                    st.rerun()
                    
        # 2. Module Reset Section
        with col_act2:
            st.markdown("##### 🔄 Reset Learner Module")
            st.caption("Modules can be reset if the learner has reached 3 failed attempts (or forced by admin).")
            
            res_learner_id = st.selectbox(
                "Select Learner for Reset:",
                options=learner_ids,
                format_func=lambda x: learner_map.get(x, x),
                key="admin_res_learner_select"
            )
            res_module_id = st.selectbox(
                "Select Module to Reset:",
                options=["module_1", "module_2", "module_3", "module_4", "module_9", "module_10"],
                key="admin_res_mod_select"
            )
            force_override = st.checkbox("Administrative Force Reset (override 3-attempt limit)", value=True, key="admin_force_reset_chk")
            if st.button("🔄 Execute Module Reset", key="btn_exec_module_reset", type="secondary"):
                success = reset_module(res_learner_id, res_module_id, force=force_override)
                if success:
                    st.success(f"Module '{res_module_id}' has been reset for {res_learner_id}!")
                else:
                    st.error("Reset failed: reset conditions not met.")

with tab_val:
    st.markdown("### 🧪 Automated Curriculum Content Validator")
    st.caption("Verifies that every module has complete labs, rubrics, term definitions, concise sentences, and working test queries.")
    
    if st.button("Run Content Validator Now", type="primary"):
        with st.spinner("Validating content structure, YAML files, and test executions..."):
            val_res = validate_all_content()
            
            if val_res["passed"]:
                st.success(f"✅ Content Validation Passed! Validated {val_res['modules_validated']} modules across Phase 1 and Phase 3.")
            else:
                st.error(f"❌ Content Validation Failed with {val_res['error_count']} errors.")
                for err in val_res["errors"]:
                    st.markdown(f"- 🔴 `{err}`")
                    
            if val_res["warning_count"] > 0:
                with st.expander(f"⚠️ Editorial Warnings ({val_res['warning_count']} items)", expanded=False):
                    for w in val_res["warnings"]:
                        st.markdown(f"- 🟡 {w}")

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
