"""Weighted resume scoring module with 0-100 total and category breakdown."""

from __future__ import annotations

import logging
from typing import Dict, List

from config import LOG_FILE, SCORE_WEIGHTS


logging.basicConfig(filename=LOG_FILE, level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("reskill.resume_scorer")


def _cap(value: int, limit: int) -> int:
    return max(0, min(limit, value))


def score_resume(
    sections: Dict[str, str],
    contact_score: int,
    matched_skills: List[str],
    missing_skills: List[str],
    bullet_stats: Dict,
) -> Dict:
    """Calculate weighted section scores and total score."""
    try:
        summary_words = len(sections.get("summary", "").split())
        if 50 <= summary_words <= 200:
            summary_score = SCORE_WEIGHTS["summary"]
        elif 25 <= summary_words < 50:
            summary_score = int(SCORE_WEIGHTS["summary"] * 0.7)
        else:
            summary_score = int(SCORE_WEIGHTS["summary"] * 0.4)

        exp_text = sections.get("experience", "")
        exp_bullets = bullet_stats.get("total_bullets", 0)
        quantified_pct = bullet_stats.get("quantified_percentage", 0)
        exp_score = int(round((min(100, (exp_bullets * 8) + quantified_pct) / 100) * SCORE_WEIGHTS["experience"]))

        edu_score = SCORE_WEIGHTS["education"] if sections.get("education") else int(SCORE_WEIGHTS["education"] * 0.35)

        total_role_skills = max(1, len(matched_skills) + len(missing_skills))
        skills_pct = int(round((len(matched_skills) / total_role_skills) * 100))
        skill_score = int(round((skills_pct / 100) * SCORE_WEIGHTS["skills"]))

        project_score = SCORE_WEIGHTS["projects"] if sections.get("projects") else int(SCORE_WEIGHTS["projects"] * 0.3)
        cert_score = SCORE_WEIGHTS["certifications"] if sections.get("certifications") else int(SCORE_WEIGHTS["certifications"] * 0.25)

        full_text = "\n".join(sections.values())
        word_count = len(full_text.split())
        has_key_sections = all(sections.get(name) for name in ["experience", "education", "skills"])
        formatting_raw = 5
        if word_count < 350 or word_count > 1000:
            formatting_raw -= 2
        if not has_key_sections:
            formatting_raw -= 2
        formatting_score = max(0, formatting_raw)

        breakdown = {
            "contact": _cap(contact_score, SCORE_WEIGHTS["contact"]),
            "summary": _cap(summary_score, SCORE_WEIGHTS["summary"]),
            "experience": _cap(exp_score, SCORE_WEIGHTS["experience"]),
            "education": _cap(edu_score, SCORE_WEIGHTS["education"]),
            "skills": _cap(skill_score, SCORE_WEIGHTS["skills"]),
            "projects": _cap(project_score, SCORE_WEIGHTS["projects"]),
            "certifications": _cap(cert_score, SCORE_WEIGHTS["certifications"]),
            "formatting": _cap(formatting_score, SCORE_WEIGHTS["formatting"]),
        }

        total_score = sum(breakdown.values())

        return {
            "total_score": _cap(total_score, 100),
            "breakdown": breakdown,
            "summary": {
                "word_count": word_count,
                "experience_bullets": exp_bullets,
                "quantified_percentage": quantified_pct,
                "skills_match_percentage": skills_pct,
                "experience_text_length": len(exp_text),
            },
        }
    except Exception:
        logger.exception("score_resume failed")
        return {
            "total_score": 0,
            "breakdown": {k: 0 for k in SCORE_WEIGHTS},
            "summary": {},
        }
