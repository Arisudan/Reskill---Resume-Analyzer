import time
from typing import List

from .models import AnalysisResult, ResumeInput
from .skills import ROLE_SKILLS, normalize_role
from .text_utils import contains_phrase, normalize_text, sanitize_and_truncate


IMPACT_KEYWORDS = ["led", "built", "improved", "optimized", "shipped"]


def _match_skills(normalized_resume: str, required_skills: List[str]) -> List[str]:
    return [skill for skill in required_skills if contains_phrase(normalized_resume, skill)]


def _score_resume(matched_count: int, required_count: int, normalized_resume: str) -> int:
    base = 20
    coverage_component = int(round((matched_count / required_count) * 70)) if required_count else 0
    impact_hits = sum(1 for keyword in IMPACT_KEYWORDS if contains_phrase(normalized_resume, keyword))
    impact_component = min(10, impact_hits * 2)
    return min(100, base + coverage_component + impact_component)


def _build_suggestions(missing_skills: List[str], score: int) -> List[str]:
    suggestions = [f"Add evidence of {skill} with a concrete project or impact metric." for skill in missing_skills[:5]]
    if score < 50:
        suggestions.append("Strengthen role alignment by highlighting direct, recent experience.")
    if not suggestions:
        suggestions.append("Resume aligns well. Improve clarity with quantified outcomes per project.")
    return suggestions


def analyze_resume(resume_input: ResumeInput) -> AnalysisResult:
    start_time = time.perf_counter()

    cleaned_text, truncated = sanitize_and_truncate(resume_input.resume_text)
    if not cleaned_text:
        elapsed_ms = int((time.perf_counter() - start_time) * 1000)
        return AnalysisResult(
            score=None,
            missing_skills=[],
            suggestions=[],
            role_used=normalize_role(resume_input.role),
            truncated=truncated,
            error="resume_text is empty",
            elapsed_ms=elapsed_ms,
        )

    role_used = normalize_role(resume_input.role)
    required_skills = ROLE_SKILLS[role_used]

    normalized_resume = normalize_text(cleaned_text)
    matched_skills = _match_skills(normalized_resume, required_skills)
    missing_skills = [skill for skill in required_skills if skill not in matched_skills]

    score = _score_resume(len(matched_skills), len(required_skills), normalized_resume)
    suggestions = _build_suggestions(missing_skills, score)

    elapsed_ms = int((time.perf_counter() - start_time) * 1000)
    return AnalysisResult(
        score=score,
        missing_skills=missing_skills,
        suggestions=suggestions,
        role_used=role_used,
        truncated=truncated,
        error=None,
        elapsed_ms=elapsed_ms,
    )
