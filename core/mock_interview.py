import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from core.db import execute_query, execute_write

LEADERSHIP_INTERVIEW_QUESTIONS = [
    {
        "id": "q1_strategy",
        "category": "Strategy & Vision",
        "title": "2-Minute AI & Data Strategy Pitch",
        "is_two_minute_drill": True,
        "prompt": "You are in the final interview with the CEO and Board. They ask: 'Walk me through your Data & AI strategy for our company over your first 90 days.'",
        "framework": "30-60-90 Day Framework: Discovery & Stakeholder Alignment -> Quick Win Pilot -> Scalable Operating Model",
        "rubric_criteria": ["business alignment", "quick wins", "operating model", "governance", "p&l impact"],
        "sample_strong_response": "Over the first 30 days, I conduct a listening tour across commercial leaders to identify high-value pain points and map our data lineage. In days 31-60, we deliver one quick-win automation pilot—recovering analyst capacity and proving immediate ROI. In days 61-90, I institute a federated Hub-and-Spoke operating model with governed semantic standards and an AI intake scoring rubric."
    },
    {
        "id": "q2_technical_judgment",
        "category": "Technical Judgment",
        "title": "Evaluating a Vendor's Enterprise LLM Claim",
        "is_two_minute_drill": False,
        "prompt": "A SaaS vendor pitches an enterprise generative AI copilot to your executive team, guaranteeing '100% zero-hallucination accuracy on internal data without fine-tuning.' How do you evaluate and challenge this claim in front of the executive committee?",
        "framework": "Probabilistic Nature of LLMs + RAG Architecture Limitations + Benchmark Verification Protocol",
        "rubric_criteria": ["probabilistic", "hallucination", "benchmark", "rag", "eval set", "guardrails"],
        "sample_strong_response": "I would advise the committee that no probabilistic language model can mathematically guarantee zero hallucination. I would require the vendor to run a 50-item enterprise evaluation benchmark against our proprietary test set, measuring precision, recall, and source citation fidelity, while establishing automated guardrails before any contract sign-off."
    },
    {
        "id": "q3_stakeholder_conflict",
        "category": "Stakeholder Management",
        "title": "Conflicting Board Metrics",
        "is_two_minute_drill": False,
        "prompt": "The VP of Sales reports 1,400 active customers to the Board, while the VP of Finance reports 1,100 active customers. Both demand that you endorse their figure as the official company truth. How do you resolve this conflict?",
        "framework": "Data Lineage Audit + Root Cause Identification + Governed Metric Standard",
        "rubric_criteria": ["lineage", "semantic model", "reconcil", "governance", "definition", "executive alignment"],
        "sample_strong_response": "Rather than taking sides, I trace the data lineage to show where definitions diverged: Sales counts trial users, while Finance counts active paying billings. I draft a governed Metric Catalog defining 'Active Paying Customer' and 'Active Trial Prospect' as distinct tiers, securing sign-off from both executives and updating our semantic layer."
    },
    {
        "id": "q4_star_prioritization",
        "category": "STAR Behavioral",
        "title": "Managing Inundation of Ad-Hoc Requests",
        "is_two_minute_drill": False,
        "prompt": "Describe a time when your analytics team was overwhelmed by ad-hoc reporting requests, stalling strategic initiatives. How did you restructure intake and prioritization?",
        "framework": "Situation -> Task -> Action -> Result (STAR)",
        "rubric_criteria": ["intake framework", "scoring rubric", "self-serve", "backlog", "impact"],
        "sample_strong_response": "Our team faced 40+ weekly Slack requests. I replaced unstructured requests with an executive intake portal scored on Business Impact, Strategic Alignment, and Effort. We automated recurring reports into self-serve dashboards, cutting ad-hoc interruptions by 65% and freeing capacity for our core predictive churn model."
    },
    {
        "id": "q5_build_vs_buy",
        "category": "Technical Judgment",
        "title": "Build vs. Buy Data Platform Decision",
        "is_two_minute_drill": False,
        "prompt": "Your senior engineering team wants to spend 9 months writing a custom in-house vector search and data pipeline. A managed cloud service solves 85% of requirements for $25k/year. How do you decide and lead this conversation with your engineers?",
        "framework": "TCO + Core Competitive Differentiation vs Commodity Infrastructure",
        "rubric_criteria": ["differentiation", "tco", "engineering cost", "opportunity cost", "time-to-value"],
        "sample_strong_response": "I evaluate build vs buy through the lens of competitive differentiation. Data ingestion is a commodity; building custom pipelines consumes expensive engineering talent without creating unique IP. We adopt the managed SaaS tool to capture immediate time-to-value, directing our engineering talent toward proprietary algorithmic models that directly drive revenue."
    },
    {
        "id": "q6_operating_model",
        "category": "Operating Model",
        "title": "Centralized vs Decentralized Analytics Topology",
        "is_two_minute_drill": False,
        "prompt": "The CFO wants to decentralize all analysts into business units to cut central overhead. What trade-offs do you present, and what organizational topology do you recommend?",
        "framework": "Federated / Hub-and-Spoke Architecture Trade-offs",
        "rubric_criteria": ["hub-and-spoke", "federated", "silo", "redundancy", "standards", "domain context"],
        "sample_strong_response": "Complete decentralization causes metric chaos, duplicate tool spending, and zero career paths for technical talent. I recommend a Hub-and-Spoke model: a central platform Hub maintaining data infrastructure, governance, and semantic standards, with embedded Spoke analysts partnered with commercial business units to drive domain velocity."
    },
    {
        "id": "q7_ai_risk",
        "category": "AI Governance",
        "title": "Mitigating AI Risk and Regulatory Compliance",
        "is_two_minute_drill": False,
        "prompt": "Our marketing team wants to connect an external LLM to our CRM database to draft automated customer retention emails. What risks do you assess and what safeguards do you require?",
        "framework": "PII Protection + Prompt Injection + Human-in-the-Loop Review",
        "rubric_criteria": ["pii", "prompt injection", "human in the loop", "guardrails", "reputation", "consent"],
        "sample_strong_response": "I identify three critical risks: PII data leakage to third-party model providers, prompt injection altering email content, and hallucinated discount promises. I mandate automated PII masking before API calls, strict temperature controls, and a mandatory human-in-the-loop review for enterprise customer emails."
    },
    {
        "id": "q8_metric_failure",
        "category": "STAR Behavioral",
        "title": "Handling an Executive Metric Error",
        "is_two_minute_drill": False,
        "prompt": "Tell me about a time when an analytical report or model produced an erroneous conclusion that reached senior leadership. How did you handle the situation?",
        "framework": "Transparency -> Rapid Containment -> Post-Mortem -> Systemic Guardrails",
        "rubric_criteria": ["ownership", "transparent", "root cause", "post-mortem", "data contract", "prevention"],
        "sample_strong_response": "When an upstream join glitch doubled reported promotional sales, I immediately informed the executive sponsor with total transparency before external dissemination. We issued the corrected numbers within 2 hours, conducted a blameless post-mortem, and instituted automated pre-commit query tests to prevent duplicate join fan-outs permanently."
    },
    {
        "id": "q9_experimentation",
        "category": "Strategy & Science",
        "title": "Interpreting A/B Test Inconclusiveness",
        "is_two_minute_drill": False,
        "prompt": "An A/B test for a new checkout recommendation model shows a +1.8% revenue uplift with a p-value of 0.14 (statistically non-significant). The Product VP wants to roll it out to 100% of users immediately. What is your recommendation?",
        "framework": "Statistical Power + Minimum Detectable Effect + False Positive Risk",
        "rubric_criteria": ["statistical significance", "p-value", "sample size", "false positive", "business risk", "holdout"],
        "sample_strong_response": "A p-value of 0.14 means there is a 14% probability that this uplift is pure random noise. I would calculate whether our sample size had sufficient statistical power. If underpowered, we extend the test duration; if powered, we evaluate engineering maintenance costs against potential true uplift and consider a staged rollout with a permanent holdout group."
    },
    {
        "id": "q10_hiring_coaching",
        "category": "Team Leadership",
        "title": "Hiring and Coaching Diverse Data Talent",
        "is_two_minute_drill": False,
        "prompt": "How do you evaluate candidates for an Analytics Manager or Senior Data Scientist role to distinguish between someone who writes clever code vs someone who drives commercial business outcomes?",
        "framework": "Technical Competence + Commercial Translation + Behavioral Judgment",
        "rubric_criteria": ["commercial", "business problem", "translation", "rubric", "communication", "coaching"],
        "sample_strong_response": "In technical interviews, I present a real ambiguous business crisis rather than leetcode puzzles. I ask them: 'Revenue dropped 10%—what are your first three queries?' I look for candidates who explain the commercial 'why' before the technical 'how', who proactively consider data cleanliness, and who speak in clear executive language."
    },
    {
        "id": "q11_git_governance",
        "category": "Engineering Governance",
        "title": "Establishing Git & Code Review Governance",
        "is_two_minute_drill": False,
        "prompt": "You take over an analytics team that currently shares SQL scripts and Python notebooks via email and local network folders. How do you lead the transition to a modern Git and GitHub version control workflow without overwhelming non-engineering analysts?",
        "framework": "Change Management -> Tooling Onboarding -> Branching Standards -> PR Review Culture",
        "rubric_criteria": ["version control", "pull request", "branch protection", "change management", "training", "audit trail"],
        "sample_strong_response": "I frame the transition around eliminating painful spreadsheet version clashes rather than enforcing software engineering dogma. I host a hands-on workshop demonstrating GitHub Desktop's visual interface so analysts don't need complex terminal commands. We establish clear branch protection rules on main, mandate that all quarterly reporting queries go through peer-reviewed Pull Requests, and institute a culture of blameless reviews focused on business logic and data grain."
    }
]

def grade_interview_response(
    question_id: str,
    response_text: str,
    response_type: str = "text"
) -> Dict[str, Any]:
    """
    Evaluates an interview response against leadership rubrics.
    Calculates score (0-100), identifies key leadership signals, and provides strengths & fixes.
    """
    q = next((item for item in LEADERSHIP_INTERVIEW_QUESTIONS if item["id"] == question_id), None)
    if not q:
        return {"score": 70.0, "feedback": "Question not found."}
        
    words = len(response_text.split())
    if words < 25:
        return {
            "score": 45.0,
            "passed": False,
            "strengths": "Answer submitted.",
            "fixes": "Response is too brief for an executive leadership interview. Elaborate on your strategic methodology, stakeholder communication, and concrete operational steps.",
            "criteria_scores": {"strategic_depth": 40, "executive_communication": 40, "action_orientation": 45}
        }
        
    lower = response_text.lower()
    criteria = q.get("rubric_criteria", [])
    matches = [c for c in criteria if c.lower() in lower]
    
    match_ratio = len(matches) / len(criteria) if criteria else 0.8
    base_score = 65.0 + (match_ratio * 30.0)
    
    # Word count calibration for 2-minute drill
    if q.get("is_two_minute_drill"):
        # Target 150 - 300 words (equivalent to 1.5 - 2 minutes spoken at 130 words/min)
        if 130 <= words <= 320:
            base_score += 5.0
        elif words < 80:
            base_score -= 10.0
            
    final_score = min(100.0, max(50.0, round(base_score, 1)))
    passed = (final_score >= 80.0)
    
    strengths = (
        f"Strong executive framing: Addressed core strategic dimensions ({', '.join(matches[:3]) if matches else 'commercial clarity'}). "
        f"Demonstrated clear command of the operational and governance balance required of a modern Data & AI leader."
    )
    
    fixes = (
        f"To elevate this to a top-tier executive pitch: Ensure you explicitly highlight P&L financial outcomes, "
        f"cite specific governance mechanisms (e.g. data contracts or metric catalogs), and quantify expected time-to-value."
    )
    
    return {
        "score": final_score,
        "passed": passed,
        "strengths": strengths,
        "fixes": fixes,
        "word_count": words,
        "criteria_scores": {
            "strategic_vision": round(final_score, 1),
            "technical_judgment": round(min(100.0, final_score + 2), 1),
            "executive_communication": round(max(50.0, final_score - 2), 1)
        }
    }

def record_interview_attempt(
    learner_id: str,
    question_id: str,
    response_type: str,
    response_text: str,
    db_path: Optional[Path] = None
) -> Dict[str, Any]:
    """Evaluates and stores mock interview response in SQLite."""
    q = next((item for item in LEADERSHIP_INTERVIEW_QUESTIONS if item["id"] == question_id), {})
    eval_result = grade_interview_response(question_id, response_text, response_type)
    
    now = datetime.now().isoformat()
    sql = """
    INSERT INTO interview_attempts (learner_id, question_id, question_text, category, response_type, response_text, score, feedback, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    execute_write(sql, (
        learner_id, question_id, q.get("prompt", ""), q.get("category", ""),
        response_type, response_text, eval_result["score"], json.dumps(eval_result), now
    ), db_path=db_path)
    
    return eval_result
