-- AI Leader Learn SQLite Database Schema

CREATE TABLE IF NOT EXISTS learners (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    track_id TEXT NOT NULL DEFAULT 'data_ai_leadership',
    current_role TEXT,
    years_of_experience INTEGER DEFAULT 5,
    target_level TEXT,
    industry TEXT,
    tools_known TEXT,
    hours_per_week INTEGER DEFAULT 10,
    start_date TEXT NOT NULL,
    created_at TEXT NOT NULL,
    last_active_at TEXT,
    email TEXT,
    password_hash TEXT,
    status TEXT DEFAULT 'active'
);

CREATE TABLE IF NOT EXISTS diagnostic_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    learner_id TEXT NOT NULL,
    total_score REAL NOT NULL,
    category_scores TEXT NOT NULL,
    starting_module TEXT NOT NULL,
    tested_out_modules TEXT NOT NULL,
    answers TEXT,
    completed_at TEXT NOT NULL,
    FOREIGN KEY (learner_id) REFERENCES learners(id)
);

CREATE TABLE IF NOT EXISTS module_progress (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    learner_id TEXT NOT NULL,
    module_id TEXT NOT NULL,
    phase_id TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'locked', -- locked, in_progress, passed, tested_out, needs_review
    mastery_score REAL DEFAULT 0.0,
    mastery_attempts INTEGER DEFAULT 0,
    project_score REAL DEFAULT 0.0,
    project_status TEXT DEFAULT 'pending', -- pending, submitted, passed, revision_needed
    lab_status TEXT DEFAULT 'pending', -- pending, passed
    started_at TEXT,
    completed_at TEXT,
    last_reset_at TEXT,
    UNIQUE(learner_id, module_id),
    FOREIGN KEY (learner_id) REFERENCES learners(id)
);

CREATE TABLE IF NOT EXISTS lesson_progress (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    learner_id TEXT NOT NULL,
    module_id TEXT NOT NULL,
    lesson_id TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'not_started', -- not_started, in_progress, completed, skipped
    chat_history TEXT,
    practice_completed INTEGER DEFAULT 0,
    completed_at TEXT,
    UNIQUE(learner_id, module_id, lesson_id),
    FOREIGN KEY (learner_id) REFERENCES learners(id)
);

CREATE TABLE IF NOT EXISTS quiz_reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    learner_id TEXT NOT NULL,
    concept_id TEXT NOT NULL,
    module_id TEXT NOT NULL,
    question_id TEXT,
    interval_days INTEGER DEFAULT 1, -- 1, 3, 7, 14
    due_date TEXT NOT NULL,
    last_reviewed_at TEXT,
    last_score REAL,
    history TEXT,
    status TEXT DEFAULT 'pending', -- pending, due, mastered
    UNIQUE(learner_id, concept_id),
    FOREIGN KEY (learner_id) REFERENCES learners(id)
);

CREATE TABLE IF NOT EXISTS misconceptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    learner_id TEXT NOT NULL,
    module_id TEXT NOT NULL,
    lesson_id TEXT,
    concept TEXT NOT NULL,
    error_type TEXT NOT NULL,
    misconception_name TEXT NOT NULL,
    context TEXT,
    occurred_at TEXT NOT NULL,
    FOREIGN KEY (learner_id) REFERENCES learners(id)
);

CREATE TABLE IF NOT EXISTS lab_attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    learner_id TEXT NOT NULL,
    module_id TEXT NOT NULL,
    lab_id TEXT NOT NULL,
    code_submitted TEXT,
    execution_status TEXT, -- success, error, timeout
    output TEXT,
    explain_line_prompt TEXT,
    explain_line_answer TEXT,
    explain_line_passed INTEGER DEFAULT 0,
    attempt_number INTEGER DEFAULT 1,
    created_at TEXT NOT NULL,
    FOREIGN KEY (learner_id) REFERENCES learners(id)
);

CREATE TABLE IF NOT EXISTS submissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    learner_id TEXT NOT NULL,
    module_id TEXT NOT NULL,
    file_path TEXT NOT NULL,
    file_name TEXT NOT NULL,
    file_type TEXT NOT NULL,
    auto_check_results TEXT,
    rubric_grade TEXT,
    strength TEXT,
    fix_1 TEXT,
    fix_2 TEXT,
    score REAL DEFAULT 0.0,
    passed INTEGER DEFAULT 0,
    submitted_at TEXT NOT NULL,
    FOREIGN KEY (learner_id) REFERENCES learners(id)
);

CREATE TABLE IF NOT EXISTS mastery_attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    learner_id TEXT NOT NULL,
    module_id TEXT NOT NULL,
    attempt_number INTEGER NOT NULL,
    score REAL NOT NULL,
    passed INTEGER NOT NULL,
    answers TEXT,
    executive_explanation TEXT,
    code_reading_answer TEXT,
    weak_concepts TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (learner_id) REFERENCES learners(id)
);

CREATE TABLE IF NOT EXISTS interview_attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    learner_id TEXT NOT NULL,
    question_id TEXT NOT NULL,
    question_text TEXT NOT NULL,
    category TEXT NOT NULL,
    response_type TEXT NOT NULL, -- text, audio
    response_text TEXT NOT NULL,
    score REAL NOT NULL,
    feedback TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (learner_id) REFERENCES learners(id)
);

CREATE INDEX IF NOT EXISTS idx_mod_prog_learner ON module_progress(learner_id);
CREATE INDEX IF NOT EXISTS idx_lesson_prog_learner ON lesson_progress(learner_id);
CREATE INDEX IF NOT EXISTS idx_quiz_due ON quiz_reviews(learner_id, due_date);
CREATE INDEX IF NOT EXISTS idx_misconception_learner ON misconceptions(learner_id);
CREATE INDEX IF NOT EXISTS idx_submissions_learner_mod ON submissions(learner_id, module_id);
