import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import streamlit as st
import pandas as pd
from config.settings import ADMIN_PASSWORD, load_track_config
from core.db import (
    get_all_learners, get_all_learners_with_activity, get_learner,
    delete_learner, execute_query
)
from core.google_drive_sync import (
    get_google_drive_sync_status, get_google_drive_sync_records, retry_pending_syncs
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
                "Email": l.get("email", "Not registered"),
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

        st.markdown("---")
        # 3. Google Drive / Sheets Sync Ledger & Status
        st.markdown("#### ☁️ Google Drive & Sheets Sync Status")
        st.caption("Live monitoring of email registrations synced to your Google Drive Sheet.")
        
        drive_status = get_google_drive_sync_status()
        col_gd1, col_gd2, col_gd3, col_gd4 = st.columns(4)
        with col_gd1:
            st.metric("Total Emails Captured", drive_status["total_emails_captured"])
        with col_gd2:
            st.metric("Synced to Google Drive", drive_status["synced_to_drive"])
        with col_gd3:
            st.metric("Pending Drive Sync", drive_status["pending_sync"])
        with col_gd4:
            is_conf = drive_status["webhook_configured"]
            st.metric("Drive Webhook", "Active ✅" if is_conf else "Pending Setup ⚠️")

        col_sync_act1, col_sync_act2 = st.columns([3, 2])
        with col_sync_act1:
            if st.button("🔄 Retry / Sync Pending Emails to Google Drive", key="btn_retry_drive_sync"):
                count = retry_pending_syncs()
                if count > 0:
                    st.success(f"Successfully synced {count} pending emails to your Google Drive Sheet!")
                elif not drive_status["webhook_configured"]:
                    st.warning("Google Sheet Webhook URL is not yet configured in `.env` (GOOGLE_SHEET_WEBHOOK_URL).")
                else:
                    st.info("All captured emails are already up-to-date in Google Drive.")
        with col_sync_act2:
            sync_records = get_google_drive_sync_records()
            if sync_records:
                import io
                csv_buffer = io.StringIO()
                import csv as py_csv
                writer = py_csv.DictWriter(csv_buffer, fieldnames=["timestamp", "learner_id", "name", "email", "role", "sync_status", "error_message"])
                writer.writeheader()
                writer.writerows(sync_records)
                st.download_button(
                    "📥 Download Email Ledger CSV",
                    data=csv_buffer.getvalue(),
                    file_name="google_drive_emails_ledger.csv",
                    mime="text/csv",
                    use_container_width=True
                )

        with st.expander("📖 How to Connect Your Google Drive Sheet (Setup Instructions)", expanded=False):
            st.markdown("""
            **How to sync learner emails directly into your Google Drive Sheet:**
            1. Open [Google Drive](https://drive.google.com) and create a new **Google Sheet** (e.g. named `AI Leader Learn - Registrations`).
            2. In the Google Sheet, add headers in Row 1: `Timestamp | Learner ID | Full Name | Email Address | Target Role`.
            3. Click **Extensions** ➔ **Apps Script**, and paste this short snippet:
            ```javascript
            function doPost(e) {
              var data = JSON.parse(e.postData.contents);
              var sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
              sheet.appendRow([data.timestamp, data.learner_id, data.name, data.email, data.role]);
              return ContentService.createTextOutput(JSON.stringify({"status": "success"})).setMimeType(ContentService.MimeType.JSON);
            }
            ```
            4. Click **Deploy** ➔ **New deployment** ➔ Select type: **Web app**.
               - Set **Execute as:** `Me`.
               - Set **Who has access:** `Anyone`.
            5. Copy the generated **Web App URL**, and paste it into `.env` as:
            ```bash
            GOOGLE_SHEET_WEBHOOK_URL="https://script.google.com/macros/s/YOUR_SCRIPT_ID/exec"
            ```
            Every new learner registration will instantly append to your Google Sheet on Google Drive!
            """)

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
