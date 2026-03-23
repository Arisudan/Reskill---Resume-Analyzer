"""Gemini-backed rewriting and improvement suggestions with cached, rate-limited calls."""

from __future__ import annotations

import json
import logging
import os
from typing import List

import streamlit as st
from dotenv import load_dotenv

from config import CACHE_TTL, GEMINI_MODEL, LOG_FILE


logging.basicConfig(filename=LOG_FILE, level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("reskill.ai_rewriter")

load_dotenv()


def _api_key() -> str:
    try:
        return st.secrets.get("GEMINI_API_KEY", "")
    except Exception:
        return os.getenv("GEMINI_API_KEY", "")


def _can_call_api() -> bool:
    if "api_calls" not in st.session_state:
        st.session_state.api_calls = 0
    return st.session_state.api_calls < 10


def _increment_api_calls() -> None:
    st.session_state.api_calls = st.session_state.get("api_calls", 0) + 1


@st.cache_data(ttl=CACHE_TTL)
def _ask_gemini_cached(api_key: str, prompt: str) -> str:
    if not api_key:
        return ""
    try:
        import google.generativeai as genai

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(GEMINI_MODEL)
        response = model.generate_content(prompt)
        return (response.text or "").strip()
    except Exception as exc:
        logger.warning("Gemini call failed: %s", exc)
        return ""


def rewrite_bullet(weak_bullet: str, job_title: str) -> str:
    """Rewrite a weak bullet into stronger STAR-style form."""
    try:
        if not _can_call_api():
            return f"Led {job_title} initiatives and delivered measurable impact by improving outcomes by 20%."

        prompt = (
            f"Rewrite this resume bullet point for a {job_title} role using strong action verbs "
            f"and quantifiable impact in STAR format. Keep it under 20 words. Original: {weak_bullet}"
        )
        result = _ask_gemini_cached(_api_key(), prompt)
        if result:
            _increment_api_calls()
            return result.splitlines()[0][:220]

        return f"Led key {job_title} initiatives, improving performance and delivery metrics with measurable business impact."
    except Exception:
        logger.exception("rewrite_bullet failed")
        return f"Led key {job_title} initiatives, improving performance and delivery metrics with measurable business impact."


def generate_summary(name: str, job_title: str, years_exp: str, top_skills: str) -> str:
    """Generate a 3-sentence professional summary."""
    try:
        if not _can_call_api():
            return (
                f"Results-driven {job_title} with {years_exp} years of experience delivering scalable solutions. "
                f"Skilled in {top_skills}. Focused on measurable impact and cross-functional collaboration."
            )

        prompt = (
            f"Write a 3-sentence professional resume summary for {name}, a {job_title} with {years_exp} years "
            f"of experience skilled in {top_skills}. Start with a strong adjective."
        )
        result = _ask_gemini_cached(_api_key(), prompt)
        if result:
            _increment_api_calls()
            return result

        return (
            f"Results-driven {job_title} with {years_exp} years of experience delivering scalable solutions. "
            f"Skilled in {top_skills}. Focused on measurable impact and cross-functional collaboration."
        )
    except Exception:
        logger.exception("generate_summary failed")
        return (
            f"Results-driven {job_title} with {years_exp} years of experience delivering scalable solutions. "
            f"Skilled in {top_skills}. Focused on measurable impact and cross-functional collaboration."
        )


def suggest_improvements(section_name: str, section_text: str) -> List[str]:
    """Return exactly 3 actionable section-level improvements."""
    fallback = [
        f"Make {section_name} more specific with measurable outcomes.",
        f"Use stronger action verbs in the {section_name} section.",
        f"Align {section_name} keywords with target job requirements.",
    ]

    try:
        if not _can_call_api():
            return fallback

        prompt = (
            f"Review this resume {section_name} section and give exactly 3 specific, actionable improvement tips. "
            f"Return as a JSON list of strings. Section text: {section_text[:2500]}"
        )
        result = _ask_gemini_cached(_api_key(), prompt)
        if not result:
            return fallback

        _increment_api_calls()
        parsed = json.loads(result)
        if isinstance(parsed, list):
            suggestions = [str(item) for item in parsed[:3]]
            if len(suggestions) == 3:
                return suggestions
        return fallback
    except Exception:
        logger.exception("suggest_improvements failed")
        return fallback
