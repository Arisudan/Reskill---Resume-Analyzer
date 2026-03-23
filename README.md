# AI Resume Analyzer MVP

A deterministic, rule-based CLI tool and **web application** that analyzes resumes and provides:
- **Score** (0–100) based on role-specific skills
- **ATS Score** (0-100) for applicant tracking system compatibility
- **Missing Skills** for target role
- **Improvement Suggestions** with actionable guidance

## Features

✅ **Web App** — Streamlit app ready for GitHub-based deployment  
✅ **CLI** — Fast, scriptable command-line interface  
✅ **SDK** — Integrate into your Python projects  
✅ Sub-millisecond execution (<1ms per analysis)  
✅ Role-based analysis (Backend, Frontend, Data Science, General)  
✅ Deterministic, reproducible output  
✅ No external APIs or ML models  
✅ Modular, testable architecture  
✅ Structured JSON output  
✅ Mobile-responsive interface  

## NEW: Streamlit Web App 🎉

### Quick Start (Web - Streamlit)
```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
# Open http://localhost:8501
```

Then:
1. Select your target role
2. Upload your resume (TXT/PDF/DOCX) or paste text
3. Get instant feedback with role score, ATS score, skills gap, and suggestions

See [QUICKSTART.md](docs/QUICKSTART.md) for all usage modes.

## Setup

### Requirements
- Python 3.8+
- **Core Analyzer**: No external dependencies (stdlib only)
- **Web App** (optional): Streamlit 1.42+

### Installation

#### Core Analyzer Only (stdlib)
```bash
# No installation needed - run directly
python -m resume_analyzer.main input.json
```

#### Web App (with Streamlit)
```bash
# Install dependencies
pip install -r requirements.txt

# Start Streamlit
streamlit run streamlit_app.py
```

## Usage

### Web App (Recommended - GUI)

```bash
# Install dependencies
pip install -r requirements.txt

# Start Streamlit app
streamlit run streamlit_app.py

# Open browser
http://localhost:8501
```

Then:
1. Enter target role (Backend, Frontend, Data Science, or General)
2. Upload resume file or paste resume text
3. Click "Analyze Resume"
4. View role score, ATS score, missing skills, and suggestions

### CLI (Programmatic)

#### Via CLI (file)
```bash
python -m resume_analyzer.main input.json
```

#### Via CLI (stdin)
```bash
cat resume.json | python -m resume_analyzer.main
```

#### Via Python
```python
from resume_analyzer import analyze_resume
from resume_analyzer.models import ResumeInput

result = analyze_resume(ResumeInput(
    role="backend_developer",
    resume_text="Your resume content here..."
))

print(result.score)
print(result.missing_skills)
print(result.suggestions)
```

## Input Format

JSON with fields:
```json
{
  "role": "backend_developer",
  "resume_text": "Your resume content here..."
}
```

### Supported Roles
- `backend_developer` → Python, APIs, SQL, Testing, Docker, Git
- `frontend_developer` → JavaScript, HTML, CSS, React, Testing, Git
- `data_scientist` → Python, SQL, ML, Statistics, Pandas, Data Visualization
- `default` → Communication, Problem Solving, Teamwork, Project Management, Documentation
- Any unknown role falls back to `default`

## Output Format

JSON with fields:
```json
{
  "score": 75,
  "ats_score": 72,
  "missing_skills": ["docker", "testing"],
  "suggestions": [
    "Add evidence of docker with a concrete project or impact metric.",
    "..."
  ],
  "role_used": "backend_developer",
  "truncated": false,
  "error": null,
  "elapsed_ms": 42
}
```

### Fields
- `score`: 0–100, null if error
- `ats_score`: 0-100, null if error
- `missing_skills`: List of role-required skills not found
- `suggestions`: Actionable improvement tips
- `role_used`: Normalized role (or "default")
- `truncated`: Whether input exceeded 12,000 char limit
- `error`: null if success, error message otherwise
- `elapsed_ms`: Execution time in milliseconds

## Scoring Logic

- **Base**: 20 points
- **Coverage**: Up to 70 points (% of skills matched)
- **Impact**: Up to 10 points (keywords: "led", "built", "improved", "optimized", "shipped")

Example:
- 4/6 skills + 2 impact keywords = 20 + 47 + 4 = **71 points**

## Testing

```bash
# Run all tests
python tests/test_resume_analyzer.py

# Run with verbose output
python -m unittest tests.test_resume_analyzer -v
```

### Test Coverage
- Input validation (empty, whitespace, truncation)
- Skill matching (case-insensitive, multi-role)
- Scoring (determinism, range, impact keywords)
- Suggestions (low-score handling, missing skills)
- Performance (<2s requirement)
- Output format (JSON serialization)
- E2E integration (full pipeline)

## Sample Usage

### Example 1: Backend Developer (Good Match)
```bash
echo '{
  "role": "backend_developer",
  "resume_text": "Senior backend engineer with 5 years in Python, SQL, Docker. Led API architecture. Strong Git practices."
}' | python -m resume_analyzer.main
```
**Output:**
```json
{
  "score": 78,
  "missing_skills": ["testing"],
  "suggestions": [
    "Add evidence of testing with a concrete project or impact metric.",
    "Resume aligns well. Improve clarity with quantified outcomes per project."
  ],
  "role_used": "backend_developer",
  "truncated": false,
  "error": null,
  "elapsed_ms": 8
}
```

### Example 2: Frontend Developer (Poor Match)
```bash
echo '{
  "role": "frontend_developer",
  "resume_text": "Accountant with spreadsheet and Excel skills."
}' | python -m resume_analyzer.main
```
**Output:**
```json
{
  "score": 21,
  "missing_skills": ["javascript", "html", "css", "react", "testing", "git"],
  "suggestions": [
    "Strengthen role alignment by highlighting direct, recent experience.",
    "Add evidence of javascript, html, css, react, testing, git..."
  ],
  "role_used": "frontend_developer",
  "truncated": false,
  "error": null,
  "elapsed_ms": 5
}
```

### Example 3: Empty Input (Error)
```
echo '{"role": "backend_developer", "resume_text": ""}' | python -m resume_analyzer.main
```
**Output:**
```json
{
  "score": null,
  "missing_skills": [],
  "suggestions": [],
  "role_used": "backend_developer",
  "truncated": false,
  "error": "resume_text is empty",
  "elapsed_ms": 2
}
```

## Architecture

```
resume_analyzer/
├── __init__.py         # Package export
├── analyzer.py         # Core analysis logic
├── models.py           # Input/Output dataclasses
├── skills.py           # Role skill definitions
├── text_utils.py       # Text normalization & matching
├── output.py           # JSON formatting
└── main.py            # CLI entry point

WEB APP:
├── app.py             # Flask application server
├── requirements.txt   # Python dependencies (Flask)
└── templates/
    └── index.html     # Input form + result display
└── static/
    └── style.css      # Responsive styling
```

### Design Principles
1. **Deterministic**: No randomness, same input = same output
2. **Fast**: <1ms execution, minimal processing
3. **Modular**: Single responsibility per module
4. **Testable**: Pure functions, explicit inputs/outputs
5. **Stateless**: No mutable globals or side effects
6. **Layered**: Core analyzer (stdlib) + optional web layer (Flask)

## Limitations & Assumptions

- **No NLP**: Rule-based skill matching (no ML)
- **Dictionary-based**: Only finds exact/close skill phrases
- **Single file**: No database, all data in-memory
- **No authentication**: CLI assumes trusted input
- **12KB limit**: Large resumes are truncated
- **Role-specific**: Only 3 predefined roles + default fallback

## Deployment

### Development Server
```bash
pip install -r requirements.txt
python app.py
```
Visit http://localhost:5000

### Production Deployment (Gunicorn)
```bash
pip install gunicorn
gunicorn --workers 4 --bind 0.0.0.0:5000 app:app
```

### Docker (Optional)
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 5000
CMD ["gunicorn", "--workers", "4", "--bind", "0.0.0.0:5000", "app:app"]
```

## Performance Characteristics

| Operation | Time | Notes |
|-----------|------|-------|
| Parse & validate | <1ms | Fast |
| Normalize text | <5ms | Linear in input size |
| Skill matching | <10ms | 6–30 skills checked |
| Score calculation | <1ms | Simple math |
| Format JSON | <2ms | Dataclass serialization |
| **Total** | **<20ms** | Well under 2s limit |

## Error Handling

| Error | Response | HTTP-Like Status |
|-------|----------|-----------------|
| Empty resume | `error: "resume_text is empty"` | 400 |
| Malformed JSON | CLI prints to stderr | 400 |
| Unknown role | Falls back to "default" | 200 |
| Large input | Truncates + sets `truncated: true` | 200 |

## Future Enhancements (Out of Scope)

- ML-based skill extraction
- API server / REST endpoint
- Database persistence
- Resume upload/parsing
- Interview question generation
- Salary recommendations
- Skill progression tracking

## License

MIT

## Support

For questions or issues, see the test suite in `test_resume_analyzer.py`.
