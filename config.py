"""Central configuration and constants for the Reskill application."""

from __future__ import annotations

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
LOG_DIR = BASE_DIR / "logs"
LOG_FILE = LOG_DIR / "app.log"

MAX_JD_CHARS = 3000
MAX_RESUME_CHARS = 12000
MAX_UPLOAD_BYTES = 5 * 1024 * 1024
CACHE_TTL = 3600
GEMINI_MODEL = "gemini-pro"

WEAK_VERBS = [
    "helped",
    "assisted",
    "worked on",
    "was responsible for",
    "in charge of",
    "participated",
    "contributed to",
    "supported",
]

STRONG_VERBS = [
    "led",
    "built",
    "engineered",
    "drove",
    "architected",
    "implemented",
    "optimized",
    "delivered",
    "automated",
    "launched",
]

STANDARD_SECTIONS = [
    "summary",
    "objective",
    "experience",
    "education",
    "skills",
    "projects",
    "certifications",
    "awards",
    "languages",
    "interests",
]

ATS_PENALTY_KEYWORDS = [
    "table",
    "image",
    "graphic",
    "icon",
    "header",
    "footer",
    "emoji",
]

SCORE_WEIGHTS = {
    "contact": 10,
    "summary": 10,
    "experience": 25,
    "education": 15,
    "skills": 20,
    "projects": 10,
    "certifications": 5,
    "formatting": 5,
}

ROLE_MAPPING_OPTIONS = [
    "general_role",
    "software_engineer",
    "data_scientist",
    "product_manager",
    "devops_engineer",
    "designer",
    "marketing",
]

SENIORITY_OPTIONS = ["Junior", "Mid", "Senior", "Lead", "Manager"]

DEFAULTS = {
    "dark_mode": True,
    "analysis_done": False,
    "resume_text": "",
    "parsed_sections": {},
    "scores": {},
    "ats_results": {},
    "jd_results": None,
    "skill_results": {},
    "bullet_results": [],
    "ai_suggestions": {},
    "report_bytes": None,
    "uploaded_filename": None,
}
