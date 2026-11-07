import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import streamlit as st
import yaml
from pathlib import Path
from config.settings import CONTENT_DIR, load_track_config
from core.db import get_learner, execute_query
from core.lab_runner import run_sql_lab, run_python_lab, verify_explain_line, record_lab_attempt
from core.mastery_gate import get_module_status

st.title("🧪 Hands-On Technical Lab")
st.markdown(
    "Run and modify real SQL queries and Python code in a safe sandbox. "
    "To pass each lab, you must run your code successfully **and** defend your logic in the mandatory *'Explain This Line'* check."
)

learner_id = st.session_state.get("active_learner_id")
if not learner_id:
    st.warning("Please select or create a learner profile on the Home page.")
    st.stop()

learner = get_learner(learner_id)
track = load_track_config()

# Find all modules with authored lab.yaml files across all phases
authored_labs = {}
for p_dir in sorted(CONTENT_DIR.iterdir()):
    if p_dir.is_dir() and p_dir.name.startswith("phase_"):
        for m_dir in sorted(p_dir.iterdir()):
            if m_dir.is_dir() and (m_dir / "lab.yaml").exists():
                with open(m_dir / "lab.yaml", "r", encoding="utf-8") as f:
                    ldata = yaml.safe_load(f)
                    mid = ldata.get("module_id")
                    if mid:
                        authored_labs[mid] = ldata

# Build module options from track config for those with labs
all_track_mods = []
for phase in track.get("phases", []):
    for m in phase.get("modules", []):
        if m["id"] in authored_labs:
            all_track_mods.append(m)

mod_options = {m["id"]: f"{m.get('code', 'M')}: {m['title']}" for m in all_track_mods}
selected_module_id = st.selectbox(
    "Select Lab Module:",
    options=list(mod_options.keys()),
    format_func=lambda x: mod_options[x],
    key="lab_module_selector"
)

lab_data = authored_labs.get(selected_module_id)
if not lab_data:
    st.info("Lab specifications are currently being outlined for this module.")
    st.stop()

mod_status = get_module_status(learner_id, selected_module_id)
is_lab_passed = (mod_status.get("lab_status") == "passed")

st.markdown(f"### {lab_data['title']}")
if is_lab_passed:
    st.success("✅ **Lab Status: Passed!** Both execution and the 'Explain This Line' defense have been verified.")
else:
    st.info("⏳ **Lab Status: Pending Completion.**")

with st.expander("📋 Lab Brief & Business Context", expanded=True):
    st.markdown(lab_data.get("brief", ""))

runner_type = lab_data.get("runner", "duckdb")
st.markdown(f"**Environment:** `{runner_type.upper()} Sandbox (Strict 5s Timeout, Isolated Filesystem)`")

# Code Editor Text Area
starter = lab_data.get("starter_code", "")
code_input = st.text_area(
    f"Edit Code / Query ({runner_type.upper()}):",
    value=starter,
    height=240,
    key=f"lab_code_{selected_module_id}"
)

# Explain This Line Section (Mandatory)
explain_cfg = lab_data.get("explain_line_check", {})
st.markdown("#### 🎯 Mandatory: Explain This Line Defense")
st.caption(f"Target Line {explain_cfg.get('line_number', 1)}: `{explain_cfg.get('target_line', '')}`")
st.markdown(f"**Prompt:** *{explain_cfg.get('prompt', 'Explain what this line does.')}*")

explain_answer = st.text_area(
    "Your Plain-English Explanation (Minimum 10 words, address business and technical implications):",
    placeholder="Explain why this line is necessary, what mathematical or relational error it prevents, and how it impacts executive reporting...",
    height=100,
    key=f"lab_explain_{selected_module_id}"
)

col_run, col_reset = st.columns([1, 4])
with col_run:
    run_btn = st.button("🚀 Run & Verify Lab", type="primary", key=f"btn_run_{selected_module_id}")

if run_btn:
    with st.spinner("Executing in sandbox..."):
        # 1. Run code in sandbox
        if runner_type == "duckdb":
            tables = lab_data.get("database_tables", {})
            exec_res = run_sql_lab(code_input, tables)
        else:
            exec_res = run_python_lab(code_input)

        exec_status = "success" if exec_res.get("success") else "error"
        output_text = exec_res.get("output", "") or exec_res.get("error", "No output.")

        # 2. Verify explain line defense
        rubric_kw = explain_cfg.get("rubric_keywords", [])
        explain_passed, explain_msg = verify_explain_line(explain_answer, rubric_kw)

        # 3. Record attempt in SQLite
        attempt_record = record_lab_attempt(
            learner_id=learner_id,
            module_id=selected_module_id,
            lab_id=lab_data.get("lab_id", "lab"),
            code_submitted=code_input,
            execution_status=exec_status,
            output=output_text,
            explain_prompt=explain_cfg.get("prompt", ""),
            explain_answer=explain_answer,
            explain_passed=explain_passed
        )

        st.markdown("### Execution Results")
        if exec_res.get("success"):
            st.success("🎉 Code executed successfully in sandbox!")
            st.markdown("**Output Preview:**")
            if "dataframe" in exec_res and exec_res["dataframe"] is not None:
                st.dataframe(exec_res["dataframe"], use_container_width=True)
            else:
                st.code(output_text)
        else:
            st.error(f"❌ Execution Error: {exec_res.get('error')}")

        st.markdown("### 'Explain This Line' Defense Evaluation")
        if explain_passed:
            st.success(f"✅ {explain_msg}")
        else:
            st.warning(f"⚠️ {explain_msg}")

        if attempt_record["lab_passed"]:
            st.balloons()
            st.success("🌟 Congratulations! You have fully passed this lab!")
            st.rerun()

st.markdown("---")
# Attempt History for this Lab
st.markdown("### 📜 Past Attempt History")
sql_hist = """
SELECT attempt_number, execution_status, explain_line_passed, created_at, code_submitted
FROM lab_attempts 
WHERE learner_id = ? AND lab_id = ?
ORDER BY id DESC LIMIT 5
"""
hist_rows = [dict(r) for r in execute_query(sql_hist, (learner_id, lab_data.get("lab_id", "lab")))]
if hist_rows:
    for h in hist_rows:
        status_icon = "🟢" if (h["execution_status"] == "success" and h["explain_line_passed"] == 1) else "🔴"
        with st.expander(f"{status_icon} Attempt #{h['attempt_number']} — {h['created_at'][:16]} (Execution: {h['execution_status']}, Explain Line: {'Passed' if h['explain_line_passed'] else 'Failed'})"):
            st.code(h["code_submitted"], language="sql" if runner_type == "duckdb" else "python")
else:
    st.caption("No previous attempts recorded.")
