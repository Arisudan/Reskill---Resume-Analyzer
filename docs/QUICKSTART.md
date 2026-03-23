# AI Resume Analyzer - Quick Start Guide

## Option 1: Web App (Recommended for Users)

### Step 1: Install Flask
```bash
pip install -r requirements.txt
```

### Step 2: Start the Server
```bash
python app.py
```

### Step 3: Open in Browser
Visit: **http://localhost:5000**

### Step 4: Use the App
1. Select your target role from dropdown
2. Paste your resume text
3. Click "Analyze Resume"
4. Review score, missing skills, and suggestions

**Features:**
- ✅ Real-time analysis
- ✅ Clean, responsive interface
- ✅ Score visualization with color coding
- ✅ Skill gap analysis
- ✅ Actionable improvement suggestions

---

## Option 2: Command Line (Developers)

### One-Time Setup (No Dependencies)
```bash
# No setup needed - core analyzer uses only Python stdlib
```

### Analyze a Resume
```bash
# From file
python -m resume_analyzer.main my_resume.json

# From stdin (pipe)
cat my_resume.json | python -m resume_analyzer.main
```

### Input Format (JSON)
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

---

## Option 3: Python SDK (Developers)

### In Your Code
```python
from resume_analyzer import analyze_resume
from resume_analyzer.models import ResumeInput

# Single analysis
result = analyze_resume(ResumeInput(
    role="backend_developer",
    resume_text="5 years Python, SQL, Docker..."
))

# Use the results
print(f"Score: {result.score}")
print(f"Missing: {result.missing_skills}")
print(f"Tips: {result.suggestions}")
```

---

## Testing

### Run All Tests
```bash
# Unit + Integration tests (21 tests)
python test_resume_analyzer.py

# Flask API tests (4 scenarios)
python test_flask_api.py

# Sample validation (6 realistic cases)
python run_all_samples.py
```

### Expected Results
- ✅ 21 unit tests pass in <10ms
- ✅ 6 sample scenarios pass
- ✅ 4 API tests pass in <5ms
- ✅ Execution time always <1ms per analysis

---

## Troubleshooting

### Issue: "ModuleNotFoundError: No module named 'flask'"
**Solution:**
```bash
pip install -r requirements.txt
```

### Issue: "Port 5000 already in use"
**Solution:** Use a different port
```bash
# In app.py, change: app.run(port=5001)
# Then visit: http://localhost:5001
```

### Issue: "Empty resume returns error"
**This is by design** — Resume must have content to analyze.

### Issue: "Input was truncated"
**Info** — Inputs over 12,000 characters are truncated. Shorten the resume or split into multiple analyses.

---

## Performance

| Operation | Time |
|-----------|------|
| Web App Load | <50ms |
| Single Analysis | <1ms |
| JSON Parsing | <1ms |
| Form Submission | <100ms (client + server) |

---

## Next Steps

### For Users
- Use the web app at http://localhost:5000
- Copy your resume text into the form
- Review the score and recommendations
- Update your resume with suggested improvements

### For Developers
- Review [README.md](README.md) for full documentation
- Check [COMPLETION_REPORT.md](COMPLETION_REPORT.md) for architecture
- Run tests to understand how the system works
- Extend the analyzer with custom skill definitions in `resume_analyzer/skills.py`

### For DevOps
- Deploy with Gunicorn: `gunicorn --workers 4 --bind 0.0.0.0:5000 app:app`
- Use Docker for containerized deployment
- See Deployment section in [README.md](README.md)

---

## Project Structure

```
.
├── resume_analyzer/       # Core analyzer (stdlib only)
│   ├── analyzer.py       # Main logic
│   ├── models.py         # Data structures
│   ├── skills.py         # Skill definitions
│   ├── text_utils.py     # Text processing
│   └── ...
├── app.py                # Flask web app
├── templates/
│   └── index.html        # Web UI
├── static/
│   └── style.css         # Styling
├── test_*.py             # Test suites
├── README.md             # Full documentation
└── requirements.txt      # Python dependencies
```

---

## Support

- **Questions?** See [README.md](README.md) for details
- **Tests failing?** Run `python test_resume_analyzer.py -v` to debug
- **Need examples?** Check `samples.json` and `test_input.json`

---

**Ready to get started? Pick an option above and dive in!** 🚀
