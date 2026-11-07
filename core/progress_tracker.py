from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from config.settings import load_track_config
from core.db import execute_query

def calculate_learner_metrics(learner_id: str, db_path: Optional[Path] = None) -> Dict[str, Any]:
    """
    Computes core summary statistics for a learner:
    - Days left (out of 90)
    - Lessons completed
    - Labs passed
    - Active streak
    - Average mastery score
    - Pace status (ahead, on_track, behind)
    - Projected finish date
    """
    from core.db import get_learner
    learner = get_learner(learner_id, db_path=db_path)
    if not learner:
        return {}
        
    start_date = datetime.fromisoformat(learner["start_date"]).date()
    today = datetime.now().date()
    elapsed_days = (today - start_date).days
    elapsed_days = max(0, elapsed_days)
    days_left = max(0, 90 - elapsed_days)
    
    # Modules progress
    sql_mods = "SELECT * FROM module_progress WHERE learner_id = ?"
    mod_rows = [dict(r) for r in execute_query(sql_mods, (learner_id,), db_path=db_path)]
    
    passed_mods = sum(1 for m in mod_rows if m["status"] in ["passed", "tested_out"])
    total_mods = 15 # 4 phases, 15 modules in curriculum
    
    # Labs passed
    labs_passed = sum(1 for m in mod_rows if m.get("lab_status") == "passed")
    
    # Lessons completed
    sql_lessons = "SELECT COUNT(*) as count FROM lesson_progress WHERE learner_id = ? AND status = 'completed'"
    les_rows = execute_query(sql_lessons, (learner_id,), db_path=db_path)
    lessons_done = les_rows[0]["count"] if les_rows else 0
    total_lessons = 60 # approx 4 lessons per module
    
    # Average mastery score across attempted modules
    scores = [m["mastery_score"] for m in mod_rows if m["mastery_score"] > 0]
    avg_score = round(sum(scores) / len(scores), 1) if scores else 0.0
    
    # Streak calculation
    sql_dates = """
    SELECT DISTINCT DATE(created_at) as act_date FROM (
        SELECT created_at FROM lab_attempts WHERE learner_id = ?
        UNION ALL
        SELECT completed_at as created_at FROM lesson_progress WHERE learner_id = ? AND completed_at IS NOT NULL
        UNION ALL
        SELECT submitted_at as created_at FROM submissions WHERE learner_id = ?
        UNION ALL
        SELECT created_at FROM mastery_attempts WHERE learner_id = ?
    ) ORDER BY act_date DESC
    """
    date_rows = [r["act_date"] for r in execute_query(sql_dates, (learner_id, learner_id, learner_id, learner_id), db_path=db_path)]
    
    streak = 0
    check_date = today
    date_set = set(date_rows)
    # Check if active today or yesterday
    if today.isoformat() in date_set:
        check_date = today
    elif (today - timedelta(days=1)).isoformat() in date_set:
        check_date = today - timedelta(days=1)
    else:
        streak = 0
        check_date = None
        
    if check_date:
        curr = check_date
        while curr.isoformat() in date_set:
            streak += 1
            curr -= timedelta(days=1)
            
    # Pace calculation
    # Planned lessons per day = 60 lessons / 90 days = 0.67 lessons/day
    expected_lessons = int(elapsed_days * (60.0 / 90.0))
    hours_per_week = learner.get("hours_per_week", 10)
    
    if lessons_done >= expected_lessons + 2:
        pace_status = "ahead"
        pace_label = "Ahead of Schedule"
        pace_color = "#10B981" # green
    elif lessons_done >= expected_lessons - 1:
        pace_status = "on_track"
        pace_label = "On Track"
        pace_color = "#2563EB" # blue
    else:
        pace_status = "behind"
        pace_label = "Behind Target Pace"
        pace_color = "#EF4444" # red
        
    # Projected finish date
    # Rate of lessons completed per elapsed day
    effective_elapsed = max(1, elapsed_days)
    daily_rate = (lessons_done + (passed_mods * 2)) / effective_elapsed
    if daily_rate > 0.05:
        remaining_units = max(0, total_lessons - lessons_done)
        projected_days_needed = int(remaining_units / daily_rate)
        projected_finish_date = (today + timedelta(days=projected_days_needed)).isoformat()
    else:
        # Default projection assuming planned hours
        projected_finish_date = (start_date + timedelta(days=105)).isoformat()
        
    return {
        "learner": learner,
        "elapsed_days": elapsed_days,
        "days_left": days_left,
        "lessons_done": lessons_done,
        "total_lessons": total_lessons,
        "labs_passed": labs_passed,
        "total_labs": total_mods,
        "passed_modules": passed_mods,
        "total_modules": total_mods,
        "average_score": avg_score,
        "streak": max(1, streak) if streak > 0 else 0,
        "pace_status": pace_status,
        "pace_label": pace_label,
        "pace_color": pace_color,
        "expected_lessons": expected_lessons,
        "projected_finish_date": projected_finish_date,
        "start_date": start_date.isoformat(),
        "today": today.isoformat()
    }

def generate_phase_gantt_chart(learner_id: str, db_path: Optional[Path] = None) -> go.Figure:
    """
    Creates a responsive Plotly Gantt / timeline chart for the 4 curriculum phases (Days 1-90).
    Highlights learner's current progress and phase positioning.
    """
    metrics = calculate_learner_metrics(learner_id, db_path=db_path)
    start_dt = datetime.fromisoformat(metrics["start_date"])
    
    phases_data = [
        {"Phase": "Phase 1: Technical Literacy", "Start": 0, "End": 20, "Color": "#3B82F6"},
        {"Phase": "Phase 2: Operating Models & Foundations", "Start": 21, "End": 50, "Color": "#8B5CF6"},
        {"Phase": "Phase 3: AI Leadership in Practice", "Start": 51, "End": 75, "Color": "#EC4899"},
        {"Phase": "Phase 4: Executive Readiness", "Start": 76, "End": 90, "Color": "#10B981"},
    ]
    
    df_gantt = []
    for p in phases_data:
        p_start = start_dt + timedelta(days=p["Start"])
        p_end = start_dt + timedelta(days=p["End"])
        df_gantt.append({
            "Task": p["Phase"],
            "Start": p_start.strftime("%Y-%m-%d"),
            "Finish": p_end.strftime("%Y-%m-%d"),
            "Duration": p["End"] - p["Start"],
            "Color": p["Color"]
        })
        
    df = pd.DataFrame(df_gantt)
    fig = px.timeline(
        df, 
        x_start="Start", 
        x_end="Finish", 
        y="Task", 
        color="Task",
        color_discrete_sequence=[p["Color"] for p in phases_data],
        title="90-Day Executive Leadership Curriculum Timeline"
    )
    
    # Add vertical reference line for today
    today_str = datetime.now().strftime("%Y-%m-%d")
    fig.add_vline(
        x=today_str, 
        line_width=2, 
        line_dash="dash", 
        line_color="#EF4444",
        annotation_text="Today (Your Position)",
        annotation_position="top right"
    )
    
    fig.update_yaxes(autorange="reversed")
    fig.update_layout(
        showlegend=False,
        height=260,
        margin=dict(l=10, r=10, t=40, b=10),
        xaxis_title="Calendar Schedule",
        yaxis_title=""
    )
    return fig

def generate_phase_progress_donuts(learner_id: str, db_path: Optional[Path] = None) -> List[Dict[str, Any]]:
    """
    Returns progress completion percentage per phase for visual donut charts.
    """
    track = load_track_config()
    sql = "SELECT module_id, status FROM module_progress WHERE learner_id = ?"
    rows = {r["module_id"]: r["status"] for r in execute_query(sql, (learner_id,), db_path=db_path)}
    
    phase_stats = []
    for phase in track.get("phases", []):
        p_mods = phase.get("modules", [])
        total = len(p_mods)
        passed = sum(1 for m in p_mods if rows.get(m["id"]) in ["passed", "tested_out"])
        pct = round((passed / total) * 100, 1) if total > 0 else 0.0
        phase_stats.append({
            "phase_id": phase["id"],
            "name": phase["name"],
            "passed": passed,
            "total": total,
            "pct": pct
        })
    return phase_stats

def generate_mastery_trend_chart(learner_id: str, db_path: Optional[Path] = None) -> go.Figure:
    """
    Plots the quiz / mastery score trend across modules with an 80% threshold line.
    """
    sql = """
    SELECT module_id, mastery_score, status 
    FROM module_progress 
    WHERE learner_id = ? AND mastery_score > 0
    ORDER BY module_id ASC
    """
    rows = [dict(r) for r in execute_query(sql, (learner_id,), db_path=db_path)]
    
    if not rows:
        # Placeholder empty figure
        fig = go.Figure()
        fig.add_annotation(text="No mastery checks completed yet", showarrow=False, font=dict(size=14))
        fig.update_layout(height=240, margin=dict(l=10, r=10, t=30, b=10))
        return fig
        
    modules = [r["module_id"].replace("module_", "M") for r in rows]
    scores = [r["mastery_score"] for r in rows]
    
    fig = go.Figure()
    # Score line
    fig.add_trace(go.Scatter(
        x=modules, 
        y=scores, 
        mode="lines+markers", 
        name="Mastery Score",
        line=dict(color="#2563EB", width=3),
        marker=dict(size=8)
    ))
    # 80% threshold line
    fig.add_trace(go.Scatter(
        x=modules,
        y=[80.0] * len(modules),
        mode="lines",
        name="80% Mastery Gate",
        line=dict(color="#EF4444", dash="dash", width=2)
    ))
    
    fig.update_layout(
        title="Module Mastery Scores vs 80% Gate",
        yaxis=dict(range=[0, 105], title="Score (%)"),
        xaxis=dict(title="Module"),
        height=260,
        margin=dict(l=10, r=10, t=40, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    return fig

def generate_misconception_heatmap(learner_id: Optional[str] = None, db_path: Optional[Path] = None) -> go.Figure:
    """
    Generates a heatmap of misconceptions grouped by concept and error type.
    If learner_id is None, generates global heatmap across all learners for Admin view.
    """
    if learner_id:
        sql = "SELECT concept, error_type, COUNT(*) as count FROM misconceptions WHERE learner_id = ? GROUP BY concept, error_type"
        params = (learner_id,)
    else:
        sql = "SELECT concept, error_type, COUNT(*) as count FROM misconceptions GROUP BY concept, error_type"
        params = ()
        
    rows = [dict(r) for r in execute_query(sql, params, db_path=db_path)]
    
    if not rows:
        fig = go.Figure()
        fig.add_annotation(text="Zero misconceptions logged yet. Clean execution!", showarrow=False, font=dict(size=14))
        fig.update_layout(height=240, margin=dict(l=10, r=10, t=30, b=10))
        return fig
        
    df = pd.DataFrame(rows)
    pivot = df.pivot(index="concept", columns="error_type", values="count").fillna(0)
    
    fig = px.imshow(
        pivot,
        labels=dict(x="Error Type", y="Concept", color="Incidents"),
        x=pivot.columns,
        y=pivot.index,
        color_continuous_scale="Reds",
        title="Diagnostic Misconception Matrix"
    )
    fig.update_layout(height=260, margin=dict(l=10, r=10, t=40, b=10))
    return fig

def generate_pace_comparison_chart(learner_id: str, db_path: Optional[Path] = None) -> go.Figure:
    """
    Generates planned vs actual lessons per week chart.
    """
    metrics = calculate_learner_metrics(learner_id, db_path=db_path)
    weeks = [f"W{i}" for i in range(1, 13)]
    # Target is ~5 lessons per week
    planned = [5 * i for i in range(1, 13)]
    
    elapsed_weeks = max(1, metrics["elapsed_days"] // 7)
    actual = []
    current_lessons = metrics["lessons_done"]
    
    for i in range(1, 13):
        if i <= elapsed_weeks:
            # Distribute actual lessons up to current week
            actual.append(min(current_lessons, int((current_lessons / elapsed_weeks) * i)))
        else:
            actual.append(None)
            
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=weeks, y=planned, mode="lines", name="Target Pace (Planned)", line=dict(color="#94A3B8", dash="dash")))
    fig.add_trace(go.Bar(x=weeks, y=actual, name="Actual Completed", marker_color="#2563EB"))
    
    fig.update_layout(
        title="Pace: Cumulative Lessons Completed vs 90-Day Target",
        yaxis=dict(title="Lessons"),
        height=260,
        margin=dict(l=10, r=10, t=40, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    return fig
