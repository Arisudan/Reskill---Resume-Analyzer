"""ATS compatibility checker with issue detection and score breakdown."""

from __future__ import annotations

import logging
import re
from typing import Dict, List

from config import ATS_PENALTY_KEYWORDS, LOG_FILE, STANDARD_SECTIONS


logging.basicConfig(filename=LOG_FILE, level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("reskill.ats_checker")


def check_ats(resume_text: str, filename: str, role_skills: List[str], matched_skills: List[str]) -> Dict:
    """Compute ATS score and human-readable issues."""
    try:
        issues: List[str] = []
        breakdown: Dict[str, int] = {}

        keyword_rate = 0
        if role_skills:
            keyword_rate = int(round((len(matched_skills) / len(role_skills)) * 100))
        breakdown["keyword_match"] = keyword_rate

        lower_name = filename.lower()
        if lower_name.endswith(".pdf"):
            file_format_score = 100
        elif lower_name.endswith(".docx"):
            file_format_score = 80
            issues.append("DOCX works, but PDF is usually safer for ATS consistency.")
        else:
            file_format_score = 60
            issues.append("TXT format is accepted but may drop formatting signals.")
        breakdown["file_format"] = file_format_score

        lower_text = resume_text.lower()
        penalty = 0
        if "|" in resume_text:
            issues.append("Possible table structures found; ATS parsers can struggle with tables.")
            penalty += 12
        if any(token in lower_text for token in ["image", "graphic", "icon", "logo"]):
            issues.append("Possible image/graphic markers detected.")
            penalty += 10

        standard_header_hits = sum(1 for section in STANDARD_SECTIONS[:6] if section in lower_text)
        header_score = int(round((standard_header_hits / 6) * 100))
        breakdown["section_headers"] = header_score
        if header_score < 70:
            issues.append("Some standard section headers are missing or uncommon.")

        special_chars = len(re.findall(r"[^\x00-\x7F]", resume_text))
        special_penalty = min(20, special_chars)
        if special_penalty > 0:
            issues.append("Special characters/emojis detected; simplify symbols for ATS parsing.")
        penalty += special_penalty

        multi_column_signal = sum(1 for line in resume_text.splitlines() if line.count("  ") >= 4)
        readability_score = max(0, 100 - min(40, multi_column_signal * 5))
        if readability_score < 70:
            issues.append("Potential multi-column formatting detected; single-column layout is safer.")
        breakdown["readability"] = readability_score

        base_score = int(round((keyword_rate * 0.45) + (file_format_score * 0.20) + (header_score * 0.2) + (readability_score * 0.15)))
        final_score = max(0, min(100, base_score - penalty // 2))

        for token in ATS_PENALTY_KEYWORDS:
            if token in lower_text and f"Contains '{token}' marker" not in issues:
                pass

        return {
            "score": final_score,
            "breakdown": breakdown,
            "issues": issues,
        }
    except Exception:
        logger.exception("check_ats failed")
        return {
            "score": 0,
            "breakdown": {"keyword_match": 0, "file_format": 0, "section_headers": 0, "readability": 0},
            "issues": ["ATS checker failed. Please retry with cleaner resume text."],
        }
