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
from core.submission_checker import save_and_evaluate_project
from core.mastery_gate import get_module_status

st.title("📁 Projects & Capstone Submissions")
st.markdown(
    "Submit your executive briefs, technical audits, and analytical notebooks here. "
    "Every deliverable undergoes automated structural checks followed by a rigorous rubric evaluation "
    "delivering **one key strength** and the **top 2 actionable fixes**."
)

learner_id = st.session_state.get("active_learner_id")
if not learner_id:
    st.warning("Please select or create a learner on the Home page.")
    st.stop()

learner = get_learner(learner_id)
track = load_track_config()

# Find all modules with authored project.yaml files across all phases
authored_projects = {}
for p_dir in sorted(CONTENT_DIR.iterdir()):
    if p_dir.is_dir() and p_dir.name.startswith("phase_"):
        for m_dir in sorted(p_dir.iterdir()):
            if m_dir.is_dir() and (m_dir / "project.yaml").exists():
                with open(m_dir / "project.yaml", "r", encoding="utf-8") as f:
                    pdata = yaml.safe_load(f)
                    mid = pdata.get("module_id")
                    if mid:
                        authored_projects[mid] = pdata

all_track_mods = []
for phase in track.get("phases", []):
    for m in phase.get("modules", []):
        if m["id"] in authored_projects:
            all_track_mods.append(m)

mod_options = {m["id"]: f"{m.get('code', 'M')}: {m['title']}" for m in all_track_mods}
selected_module_id = st.selectbox(
    "Select Project Module:",
    options=list(mod_options.keys()),
    format_func=lambda x: mod_options[x],
    key="project_module_selector"
)

proj_data = authored_projects.get(selected_module_id)
if not proj_data:
    st.info("Project brief is currently being loaded for this module.")
    st.stop()

mod_status = get_module_status(learner_id, selected_module_id)
proj_score = mod_status.get("project_score", 0.0)
proj_status = mod_status.get("project_status", "pending")

st.markdown(f"### {proj_data['title']}")
if proj_status == "passed":
    st.success(f"✅ **Project Status: Passed! Score: {proj_score}%** (Resubmission allowed to improve grade)")
elif proj_status == "revision_needed":
    st.warning(f"⚠️ **Project Status: Revision Needed. Score: {proj_score}%** (Review the feedback below and resubmit)")
else:
    st.info("⏳ **Project Status: Pending Submission.**")

with st.expander("📖 Executive Business Scenario & Requirements", expanded=True):
    st.markdown(proj_data.get("scenario", ""))
    st.markdown("#### Mandatory Sections:")
    for s in proj_data.get("required_sections", []):
        st.markdown(f"- 📄 `{s}`")
    st.markdown(f"**Target Length:** `{proj_data.get('min_words', 300)} - {proj_data.get('max_words', 1500)} words`")
    st.markdown(f"**Allowed Formats:** `{', '.join(proj_data.get('allowed_extensions', []))}`")

# File Uploader
st.markdown("### 📤 Upload Deliverable")
uploaded_file = st.file_uploader(
    "Upload your project file (DOCX, PPTX, PDF, XLSX, CSV, MD, TXT, SQL, IPYNB, PY):",
    type=["docx", "pptx", "pdf", "xlsx", "csv", "md", "txt", "sql", "ipynb", "py"],
    key=f"file_uploader_{selected_module_id}"
)

if uploaded_file is not None:
    st.write(f"📁 Selected: **{uploaded_file.name}** ({round(uploaded_file.size / 1024, 1)} KB)")
    
    if st.button("🚀 Submit for Automated Evaluation & Rubric Grading", type="primary"):
        with st.spinner("Analyzing document structure, sections, and executive rubric..."):
            file_bytes = uploaded_file.read()
            eval_result = save_and_evaluate_project(
                learner_id=learner_id,
                module_id=selected_module_id,
                file_name=uploaded_file.name,
                file_bytes=file_bytes,
                project_config=proj_data
            )
            
            autochecks = eval_result["autochecks"]
            grading = eval_result["grading"]
            
            st.markdown("---")
            st.markdown("### 📊 Evaluation Results")
            
            # Autochecks summary
            with st.expander(f"⚙️ Automated Structural Checks ({autochecks['score_pct']}%)", expanded=True):
                for chk in autochecks.get("checks", []):
                    icon = "✅" if chk["passed"] else "❌"
                    st.markdown(f"{icon} **{chk['name']}:** {chk['detail']}")
                    
            # Rubric score
            if grading["passed"]:
                st.balloons()
                st.success(f"🎉 **Passing Grade: {grading['final_score']}%** (Threshold: >=80%)")
            else:
                st.error(f"❌ **Grade: {grading['final_score']}%** (Requires >=80% to pass)")
                
            st.markdown("#### 🌟 Key Executive Strength:")
            st.info(grading["strength"])
            
            st.markdown("#### 🛠️ Top 2 Recommended Fixes:")
            st.warning(f"1. {grading['fix_1']}\n\n2. {grading['fix_2']}")
            
            st.rerun()

st.markdown("---")
# Submission History
st.markdown("### 📜 Past Submissions for This Module")
sql_subs = """
SELECT id, file_name, score, passed, strength, fix_1, fix_2, submitted_at
FROM submissions 
WHERE learner_id = ? AND module_id = ?
ORDER BY id DESC
"""
sub_rows = [dict(r) for r in execute_query(sql_subs, (learner_id, selected_module_id))]
if sub_rows:
    for s in sub_rows:
        icon = "🟢" if s["passed"] else "🔴"
        with st.expander(f"{icon} {s['file_name']} — Score: {s['score']}% ({s['submitted_at'][:16]})"):
            st.markdown(f"**Strength:** {s.get('strength', 'N/A')}")
            st.markdown(f"**Fix 1:** {s.get('fix_1', 'N/A')}")
            st.markdown(f"**Fix 2:** {s.get('fix_2', 'N/A')}")
else:
    st.caption("No previous submissions found for this module.")
