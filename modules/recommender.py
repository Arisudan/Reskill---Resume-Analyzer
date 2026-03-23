"""Maps missing skills to courses and suggests matching job roles."""

from __future__ import annotations

import json
import logging
from typing import Dict, List

import streamlit as st

from config import DATA_DIR, LOG_FILE


logging.basicConfig(filename=LOG_FILE, level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("reskill.recommender")


@st.cache_data
def _load_recommendation_data() -> Dict:
    path = DATA_DIR / "job_roles.json"
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def recommend_courses_and_jobs(missing_skills: List[str], matched_skills: List[str]) -> Dict[str, List[Dict]]:
    """Return top course recommendations and role recommendations."""
    try:
        data = _load_recommendation_data()
        course_map = data.get("course_map", {})
        role_to_skills = data.get("role_to_skills", {})

        courses: List[Dict] = []
        for skill in missing_skills[:5]:
            record = course_map.get(skill.lower())
            if record:
                courses.append({"skill": skill, **record})

        if len(courses) < 3:
            for skill_key, record in list(course_map.items())[:8]:
                if all(c.get("skill", "").lower() != skill_key for c in courses):
                    courses.append({"skill": skill_key, **record})
                if len(courses) >= 3:
                    break

        role_scores: List[Dict] = []
        matched_set = set(skill.lower() for skill in matched_skills)
        for role, skills in role_to_skills.items():
            if not skills:
                continue
            overlap = sum(1 for skill in skills if skill.lower() in matched_set)
            pct = int(round((overlap / len(skills)) * 100))
            role_scores.append({"role": role, "match": pct})

        role_scores.sort(key=lambda item: item["match"], reverse=True)
        job_roles = role_scores[:3]

        return {
            "courses": courses[:5],
            "job_roles": job_roles,
        }
    except Exception:
        logger.exception("recommend_courses_and_jobs failed")
        return {
            "courses": [],
            "job_roles": [],
        }
