import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import streamlit as st
from datetime import datetime, timedelta
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from config.settings import load_track_config
from core.db import get_learner, execute_query
from core.progress_tracker import (
    calculate_learner_metrics, generate_phase_gantt_chart,
    generate_phase_progress_donuts, generate_mastery_trend_chart,
    generate_misconception_heatmap, generate_pace_comparison_chart
)

st.title("📊 Executive Dashboard")

learner_id = st.session_state.get("active_learner_id")
if not learner_id:
    st.warning("Please select or create a learner on the Home page.")
    st.stop()

learner = get_learner(learner_id)
metrics = calculate_learner_metrics(learner_id)
track = load_track_config()

# Top Metric Banner
col1, col2, col3, col4, col5 = st.columns(5)
with col1:
    st.metric("Days Remaining", f"{metrics['days_left']} / 90d", f"Day {metrics['elapsed_days']} elapsed")
with col2:
    st.metric("Lessons Completed", f"{metrics['lessons_done']} / {metrics['total_lessons']}")
with col3:
    st.metric("Labs Passed", f"{metrics['labs_passed']} / {metrics['total_labs']}")
with col4:
    st.metric("Active Streak", f"{metrics['streak']} Days", "🔥 Daily Consistency")
with col5:
    st.metric("Avg Mastery Score", f"{metrics['average_score']}%", "Threshold: 80%")

# Honest Pace Status Banner
pace_status = metrics["pace_status"]
projected_date = metrics["projected_finish_date"][:10]
if pace_status == "behind":
    st.error(
        f"⚠️ **Pacing Alert: Behind Target Schedule.** "
        f"At your current completion rate ({metrics['lessons_done']} lessons completed vs {metrics['expected_lessons']} planned by Day {metrics['elapsed_days']}), "
        f"your projected completion date has shifted to **{projected_date}**. "
        f"We recommend increasing weekly hours from {learner.get('hours_per_week', 10)}h to {learner.get('hours_per_week', 10) + 4}h to realign with the 90-day target."
    )
elif pace_status == "ahead":
    st.success(
        f"🚀 **Ahead of Schedule!** Excellent execution velocity. Projected finish date: **{projected_date}**."
    )
else:
    st.info(
        f"🎯 **On Track.** You are pacing according to your 90-day executive plan. Projected finish date: **{projected_date}**."
    )

st.markdown("---")

# Visual 1: 90-Day Timeline (Plotly Gantt)
st.markdown("### 🗓️ 90-Day Executive Roadmap Timeline")
fig_gantt = generate_phase_gantt_chart(learner_id)
st.plotly_chart(fig_gantt, use_container_width=True, key="dashboard_gantt_chart")

# Visual 2: Phase Progress Donut Cards
st.markdown("### 🍩 Phase Completion Breakdown")
donuts = generate_phase_progress_donuts(learner_id)
cols_donut = st.columns(len(donuts))

for idx, p_stat in enumerate(donuts):
    with cols_donut[idx]:
        fig_donut = go.Figure(data=[go.Pie(
            values=[p_stat["passed"], max(0, p_stat["total"] - p_stat["passed"])],
            hole=0.7,
            marker_colors=["#2563EB", "#E2E8F0"],
            textinfo="none"
        )])
        fig_donut.update_layout(
            showlegend=False,
            height=130,
            margin=dict(l=10, r=10, t=10, b=10),
            annotations=[dict(text=f"<b>{int(p_stat['pct'])}%</b>", x=0.5, y=0.5, font_size=16, showarrow=False)]
        )
        st.plotly_chart(fig_donut, use_container_width=True, key=f"donut_chart_{p_stat['phase_id']}")
        st.markdown(f"<p style='text-align:center; font-size: 0.85em; font-weight: bold;'>{p_stat['name'].split(':')[0]}<br><span style='color: #64748B; font-weight: normal;'>{p_stat['passed']}/{p_stat['total']} Modules</span></p>", unsafe_allow_html=True)

# Curriculum Module Status Grid
st.markdown("### 📚 Curriculum Modules & Mastery Gates")
sql_mods = "SELECT * FROM module_progress WHERE learner_id = ?"
mod_status_map = {r["module_id"]: dict(r) for r in execute_query(sql_mods, (learner_id,))}

for phase in track.get("phases", []):
    with st.expander(f"{phase['name']} (Days {phase['day_range'][0]} - {phase['day_range'][1]})", expanded=(phase["id"] == "phase_1")):
        cols_m = st.columns(len(phase.get("modules", [])))
        for m_idx, mod in enumerate(phase.get("modules", [])):
            with cols_m[m_idx]:
                mid = mod["id"]
                info = mod_status_map.get(mid, {})
                status = info.get("status", "locked")
                
                status_badges = {
                    "passed": "🟢 Passed",
                    "tested_out": "⚡ Tested Out",
                    "in_progress": "🔵 In Progress",
                    "needs_review": "🔴 Needs Review (Retry)",
                    "locked": "🔒 Locked"
                }
                badge = status_badges.get(status, "🔒 Locked")
                
                st.markdown(
                    f"""
                    <div style="border: 1px solid #CBD5E1; border-radius: 6px; padding: 10px; margin-bottom: 8px; min-height: 120px;">
                        <span style="font-size: 0.75em; color: #64748B; font-weight: bold;">{mod.get('code', 'M')}</span>
                        <h5 style="margin: 4px 0; font-size: 0.9em;">{mod['title']}</h5>
                        <p style="margin: 0; font-size: 0.8em; font-weight: bold;">{badge}</p>
                        <p style="margin: 2px 0 0 0; font-size: 0.75em; color: #64748B;">Mastery: {info.get('mastery_score', 0.0)}%</p>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

st.markdown("---")

# Visual 3 & 4: Mastery Trend and Pace Comparison
col_chart1, col_chart2 = st.columns(2)
with col_chart1:
    fig_trend = generate_mastery_trend_chart(learner_id)
    st.plotly_chart(fig_trend, use_container_width=True, key="dashboard_mastery_trend")

with col_chart2:
    fig_pace = generate_pace_comparison_chart(learner_id)
    st.plotly_chart(fig_pace, use_container_width=True, key="dashboard_pace_comparison")

# Visual 5: Misconception Heatmap & Lab Attempts Streak
col_heat, col_streak = st.columns(2)
with col_heat:
    st.markdown("#### 🔍 Diagnosed Misconception Matrix")
    st.caption("Identifies technical error types logged during check questions and labs.")
    fig_heat = generate_misconception_heatmap(learner_id)
    st.plotly_chart(fig_heat, use_container_width=True, key="dashboard_misconception_heatmap")

with col_streak:
    st.markdown("#### 📅 Weekly Lab Activity & Activity Streak")
    # Query lab attempts per week
    sql_labs = """
    SELECT strftime('%Y-W%W', created_at) as week, COUNT(*) as attempts
    FROM lab_attempts WHERE learner_id = ?
    GROUP BY week ORDER BY week DESC LIMIT 8
    """
    lab_rows = execute_query(sql_labs, (learner_id,))
    if lab_rows:
        df_labs = pd.DataFrame([dict(r) for r in lab_rows])
        fig_lab_bar = px.bar(df_labs, x="week", y="attempts", title="Lab Submissions per Week", color_discrete_sequence=["#10B981"])
        fig_lab_bar.update_layout(height=260, margin=dict(l=10, r=10, t=30, b=10))
        st.plotly_chart(fig_lab_bar, use_container_width=True, key="dashboard_lab_attempts_bar")
    else:
        st.info("No hands-on lab attempts recorded yet. Jump to the Lab page to execute real queries.")
