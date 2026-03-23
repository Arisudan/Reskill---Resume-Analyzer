"""Extracts skills using skills database, spaCy tokenization, and fuzzy matching."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Dict, List, Tuple

import streamlit as st

from config import DATA_DIR, LOG_FILE


logging.basicConfig(filename=LOG_FILE, level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("reskill.skill_extractor")


@st.cache_resource
def load_nlp():
    """Load spaCy model once per process; fallback to blank English model."""
    try:
        import spacy

        return spacy.load("en_core_web_sm")
    except Exception:
        import spacy

        return spacy.blank("en")


@st.cache_data
def load_skills_database() -> Dict[str, List[str]]:
    """Load categorized skills database."""
    db_path = DATA_DIR / "skills_database.json"
    with db_path.open("r", encoding="utf-8") as file:
        return json.load(file)


@st.cache_data
def load_job_roles() -> Dict[str, dict]:
    roles_path = DATA_DIR / "job_roles.json"
    with roles_path.open("r", encoding="utf-8") as file:
        return json.load(file)


def _flatten_skills(skills_db: Dict[str, List[str]]) -> List[str]:
    all_skills: List[str] = []
    for values in skills_db.values():
        all_skills.extend(values)
    return sorted(set(skill.lower() for skill in all_skills))


def _alias_normalization(token: str) -> str:
    aliases = {
        "js": "javascript",
        "ts": "typescript",
        "k8s": "kubernetes",
        "postgres": "postgresql",
        "ml": "machine learning",
        "ai": "artificial intelligence",
        "gcp": "google cloud platform",
    }
    return aliases.get(token.lower(), token.lower())


def _fuzzy_match(token: str, candidates: List[str]) -> Tuple[str, int]:
    from rapidfuzz import fuzz

    best_skill = ""
    best_score = -1
    for candidate in candidates:
        score = fuzz.ratio(token, candidate)
        if score > best_score:
            best_skill = candidate
            best_score = score
    return best_skill, best_score


def extract_skills(resume_text: str, role_key: str, sections: Dict[str, str]) -> Dict[str, List[str]]:
    """Return matched, missing, and partial skills for the selected role."""
    try:
        nlp = load_nlp()
        skills_db = load_skills_database()
        job_roles = load_job_roles()

        all_skills = _flatten_skills(skills_db)

        role_skills = [s.lower() for s in job_roles.get("role_to_skills", {}).get(role_key, [])]
        if not role_skills:
            role_skills = [s.lower() for s in job_roles.get("role_to_skills", {}).get("general_role", [])]

        focus_text = "\n".join([
            sections.get("skills", ""),
            sections.get("experience", ""),
            sections.get("projects", ""),
            resume_text,
        ])

        doc = nlp(focus_text)
        tokens = set()
        for token in doc:
            if token.is_alpha and len(token.text) > 1:
                tokens.add(_alias_normalization(token.text))

        normalized_resume = focus_text.lower()
        matched = set()
        partial = set()

        for skill in role_skills:
            if skill in normalized_resume:
                matched.add(skill)
                continue
            if skill in tokens:
                matched.add(skill)
                continue

            for token in list(tokens)[:500]:
                fuzzy_skill, fuzzy_score = _fuzzy_match(token, [skill])
                if fuzzy_score >= 88 and fuzzy_skill == skill:
                    matched.add(skill)
                    break
                if 75 <= fuzzy_score < 88 and fuzzy_skill == skill:
                    partial.add(skill)

        missing = [skill for skill in role_skills if skill not in matched and skill not in partial]

        return {
            "matched": sorted(matched),
            "partial": sorted(partial),
            "missing": sorted(missing),
            "all_role_skills": sorted(set(role_skills)),
            "detected_pool_size": len(all_skills),
        }
    except Exception:
        logger.exception("extract_skills failed")
        return {
            "matched": [],
            "partial": [],
            "missing": [],
            "all_role_skills": [],
            "detected_pool_size": 0,
        }
