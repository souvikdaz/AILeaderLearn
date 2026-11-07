# AI Leader Learn 🎯
### 90-Day Executive Accelerator for Data & AI Leadership

[![Python 3.9+](https://img.shields.io/badge/Python-3.9%2B-blue.svg)](https://www.python.org/)
[![Streamlit 1.50+](https://img.shields.io/badge/Streamlit-1.50%2B-FF4B4B.svg)](https://streamlit.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Tests Passing](https://img.shields.io/badge/Tests-33%20Passed-brightgreen.svg)]()

**AI Leader Learn** is a production-grade Streamlit web application designed to transition experienced MIS and recurring reporting managers into hands-on Data & AI leaders within 90 days. 

The learner is **not** becoming a production software engineer. Instead, they build technical judgment to:
1. **Read, run, modify, and debug small code and queries** with AI assistance.
2. **Prototype AI workflows** (RAG, prompt evaluation, classification).
3. **Judge the technical work of their engineering and data teams**.
4. **Bridge Excel/MIS concepts** directly into enterprise semantic models, data contracts, and board-level strategy.

The app teaches, quizzes, adapts, and **strictly blocks progress until mastery (>=80%) is demonstrated**.

---

## 🚀 Quickstart & Local Installation

### 1. Clone the Repository
```bash
git clone https://github.com/souvikdaz/AILeaderLearn.git
cd AILeaderLearn
```

### 2. Set Up Virtual Environment & Dependencies
```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Configure Environment Variables
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Key configuration values in `.env`:
- `ADMIN_PASSWORD`: Password for the administrative console (default: `Flound3r2766@00`).
- `DB_PATH`: SQLite database path (default: `db/aileaderlearn.db`).
- `GEMINI_API_KEY`: *(Optional)* API key for Google Gemini model calls. If omitted, the application uses an intelligent deterministic leadership tutor engine offline.

### 4. Seed Initial Data (Pre-Populates 2 Realistic Learners)
```bash
python scripts/seed_data.py
```
This populates:
- **Priya Sharma** (Mid-Phase 1): Completed Module 1, working on Module 2 with an unfinished lab, failed mastery attempt (60%), and weak concepts logged.
- **Marcus Vance** (Phase 2): Tested out of Modules 1 & 2 via placement, passed Modules 3 & 4, submitted capstone project, with active spaced review items due today.

### 5. Launch the Streamlit App
```bash
streamlit run app.py
```
Open your browser at `http://localhost:8501`.

---

## 📐 Architecture & Multi-Page Layout

The app is built on Streamlit using `st.navigation`:

| Section | Page | Description |
| :--- | :--- | :--- |
| **Learner Setup** | `1_Home.py` | Create or switch between multiple learner profiles (target level, hours/week, baseline). |
| | `2_Placement.py` | 22 scenario questions across Excel, SQL, Python, AI, and Leadership. Sets starting module and unlocks test-out modules. |
| **Curriculum** | `3_Dashboard.py` | Plotly Gantt timeline, phase donuts, mastery score trend (80% gate), pace projection, and misconception heatmap. |
| | `4_Learn.py` | Concept explanation (<300 words), line-by-line worked code, and AI tutor chat (`st.chat_message`). |
| | `5_Lab.py` | Hands-on sandboxed code execution (DuckDB/Python), output preview, and mandatory "Explain This Line" defense. |
| | `6_Quiz.py` | Spaced repetition queue (1, 3, 7, 14 days) with overdue/due today counts. |
| | `7_Mastery.py` | Module mastery check (MCQs, Code Reading, C-Suite Defense). Enforces 80% threshold and 3-attempt limit. |
| **Portfolio & Career** | `8_Projects.py` | Project briefs, file uploader for 10 formats (`.docx`, `.pptx`, `.sql`, `.ipynb`), autochecks, and rubric grading. |
| | `9_Portfolio.py` | Curated case studies and verified labs. Markdown preview and one-click ZIP export. |
| | `10_Mock_Interview.py` | 10 leadership interview questions (STAR, technical judgment, strategy) with text or audio (`st.audio_input`). |
| | `11_Career_Readiness.py`| Live market postings benchmark, gap analysis, positioning statement, and 10-hour weekly search routine. |
| **Administration** | `12_Admin.py` | Content validator runner, global learner telemetry, module resets, and lab execution logs. |

---

## 🔒 Mastery Gate & Progress Rules (Non-Negotiable)

1. **80% Threshold**: A module passes only when the learner achieves:
   - **>= 80%** on the Module Mastery Check, **AND**
   - **>= 80%** on the Capstone Project Rubric, **AND**
   - **Passed** on the Hands-On Lab (Execution + "Explain This Line" check).
2. **Sequential Unlocking**: Subsequent modules remain strictly locked until the prerequisite passes or is tested out.
3. **Attempt Limit**: Maximum of **3 attempts** per mastery check. After 3 failures, the module status transitions to `needs_review` and offers a module reset.
4. **Spaced Review Queue**: Concepts from completed modules return at intervals of **1, 3, 7, and 14 days**. A failed review resets the interval to 1 day.

---

## 🧪 Lab Sandbox & Security Isolation

- **SQL Labs**: Execute inside in-memory **DuckDB** instances with CSV data pre-loaded. File exports (`COPY`, `EXPORT`), database attachments, and network socket calls are blocked.
- **Python Labs**: Execute in an isolated Python subprocess with a strict **5-second timeout**, no internet access proxies, and blocked OS/socket modules.
- **Explain This Line Defense**: A learner cannot pass a lab solely by writing working code; they must explain the business and technical purpose of highlighted critical lines in plain English.

---

## 🛠️ Adding a New Learner Profile

1. Open the app and navigate to **Home / Learners**.
2. Click the **Create New Learner** tab.
3. Enter your details:
   - Full Name, Current Role, Years of Experience, Industry Domain.
   - Target Leadership Role (e.g. *Head of Analytics*, *AI Program Lead*).
   - Weekly Hours Commitment (e.g. 10 hours/week).
   - Tools known.
4. Click **Create Profile & Start Diagnostic**.
5. Complete the 22-question **Placement Diagnostic** to calculate your starting module and qualify for module test-outs.

---

## 🧭 Adding a New Track

Tracks are configured as modular YAML files in `config/tracks/`:
1. Create a new YAML file: `config/tracks/<track_id>.yaml`.
2. Define track metadata:
   - `track_id`, `title`, `description`
   - `market_research`: Source and date of job market analysis.
   - `skills_by_market_demand`: Ordered list of competencies with market demand percentages and deliverables.
   - `phases`: 4 phases across 90 days with constituent modules.
3. Switch the active track in `config/settings.py` or load dynamically via the curriculum loader.

---

## ✍️ Content Authoring Guide & Validator

All curriculum content lives in `content/` as structured YAML files:
```
content/phase_1/
├── module_1_data_flow/
│   ├── lessons.yaml      # 4-6 lessons (<300 words, line-by-line code explanation)
│   ├── lab.yaml          # Starter code, expected query, and explain-this-line check
│   ├── mastery.yaml      # MCQs, code reading, and executive explanation
│   └── project.yaml      # Scenario brief, required sections, and rubric criteria
```

### The Content Validator (`core/content_validator.py`)
To enforce high curriculum quality, run the validator:
```bash
python -c "from core.content_validator import validate_all_content; print(validate_all_content())"
```
The validator automatically verifies:
- Every module has a mastery check, lab, project, and rubric.
- Every technical term is defined upon first appearance.
- Flags sentences over 25 words to enforce concise executive clarity.
- Flags any code block without a plain-English line explanation.
- Confirms that every lab's test query executes cleanly in the sandbox.

---

## ☁️ Deploying to Streamlit Community Cloud

When deploying to [Streamlit Community Cloud](https://streamlit.io/cloud):
1. Push your repository to GitHub.
2. In the Streamlit Cloud dashboard, click **New App** and select `souvikdaz/AILeaderLearn`, branch `main`, main file `app.py`.
3. In **Advanced Settings -> Secrets**, add your secrets using Streamlit's secrets manager (do **not** commit `.env` to GitHub):
   ```toml
   ADMIN_PASSWORD = "your_secure_admin_password"
   GEMINI_API_KEY = "your_gemini_api_key_optional"
   ```
4. Streamlit Cloud will install dependencies from `requirements.txt` and launch the app.

---

## 🧪 Running Unit Tests

The test suite covers mastery gates, spaced review, pace projections, placement diagnostics, lab runner sandboxes, submission autochecks, content validation, and Streamlit flows:
```bash
pytest tests/ -v
```
All 33 unit tests execute in ~2.5 seconds.
