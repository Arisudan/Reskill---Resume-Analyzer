"""Detects and splits resume text into standard named sections."""

from __future__ import annotations

import logging
import re
from typing import Dict

from config import LOG_FILE, STANDARD_SECTIONS


logging.basicConfig(filename=LOG_FILE, level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("reskill.section_detector")


SECTION_MAP = {
    "summary": [r"summary", r"objective", r"profile", r"about"],
    "experience": [r"experience", r"work history", r"professional experience", r"employment"],
    "education": [r"education", r"academic", r"qualification"],
    "skills": [r"skills", r"technical skills", r"tech skills", r"core competencies"],
    "projects": [r"projects", r"project experience", r"key projects"],
    "certifications": [r"certifications", r"licenses", r"certificates"],
    "awards": [r"awards", r"achievements", r"honors"],
    "languages": [r"languages", r"language proficiency"],
    "interests": [r"interests", r"hobbies"],
}


def _normalize_header(line: str) -> str:
    return re.sub(r"[^a-z ]+", "", line.strip().lower())


def split_sections(resume_text: str) -> Dict[str, str]:
    """Return a dictionary mapping section name to section text."""
    try:
        lines = [line.strip() for line in resume_text.splitlines() if line.strip()]
        sections = {name: "" for name in STANDARD_SECTIONS}
        current = "summary"

        for line in lines:
            header = _normalize_header(line)
            switched = False
            for section, patterns in SECTION_MAP.items():
                if any(re.search(rf"\b{pattern}\b", header) for pattern in patterns):
                    current = section
                    switched = True
                    break
            if switched:
                continue
            sections[current] += (line + "\n")

        return {k: v.strip() for k, v in sections.items()}
    except Exception:
        logger.exception("split_sections failed")
        return {name: "" for name in STANDARD_SECTIONS}
