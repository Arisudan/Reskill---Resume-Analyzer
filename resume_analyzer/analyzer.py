import time
from collections import Counter
from typing import Dict, List, Set

from .models import AnalysisResult, ResumeInput
from .skills import ROLE_SKILLS, normalize_role
from .text_utils import contains_phrase, normalize_text, sanitize_and_truncate


IMPACT_KEYWORDS = ["led", "built", "improved", "optimized", "shipped"]

ACTION_VERBS = {
    "designed",
    "implemented",
    "delivered",
    "reduced",
    "increased",
    "optimized",
    "launched",
    "built",
    "led",
    "migrated",
    "automated",
}

STOPWORDS = {
    "the",
    "and",
    "with",
    "for",
    "from",
    "that",
    "this",
    "your",
    "you",
    "our",
    "their",
    "have",
    "has",
    "had",
    "will",
    "would",
    "can",
    "should",
    "into",
    "about",
    "role",
    "team",
    "years",
    "experience",
}

SKILL_SYNONYMS: Dict[str, List[str]] = {
    "apis": ["api", "rest api", "graphql", "microservices"],
    "machine learning": ["ml", "predictive modeling", "model training"],
    "data visualization": ["visualization", "dashboard", "tableau", "power bi"],
    "testing": ["unit test", "integration test", "pytest", "jest", "qa"],
    "react": ["react.js", "reactjs", "next.js"],
}


def _match_skills(normalized_resume: str, required_skills: List[str]) -> List[str]:
    matched: List[str] = []
    for skill in required_skills:
        phrases = [skill] + SKILL_SYNONYMS.get(skill, [])
        if any(contains_phrase(normalized_resume, phrase) for phrase in phrases):
            matched.append(skill)
    return matched


def _score_resume(matched_count: int, required_count: int, normalized_resume: str) -> int:
    base = 20
    coverage_component = int(round((matched_count / required_count) * 70)) if required_count else 0
    impact_hits = sum(1 for keyword in IMPACT_KEYWORDS if contains_phrase(normalized_resume, keyword))
    impact_component = min(10, impact_hits * 2)
    return min(100, base + coverage_component + impact_component)


def _extract_keywords(text: str, min_len: int = 4, top_k: int = 20) -> List[str]:
    tokens = [token for token in normalize_text(text).split() if len(token) >= min_len and token not in STOPWORDS]
    frequency = Counter(tokens)
    return [word for word, _ in frequency.most_common(top_k)]


def _compute_ats_score(cleaned_text: str, normalized_resume: str) -> int:
    length = len(cleaned_text)
    action_hits = sum(1 for verb in ACTION_VERBS if contains_phrase(normalized_resume, verb))
    metric_hits = sum(ch.isdigit() for ch in cleaned_text)

    sections = [
        "experience",
        "skills",
        "projects",
        "education",
        "summary",
        "certification",
    ]
    section_hits = sum(1 for section in sections if contains_phrase(normalized_resume, section))

    length_score = 0
    if 450 <= length <= 8000:
        length_score = 25
    elif 250 <= length < 450:
        length_score = 18
    elif 120 <= length < 250:
        length_score = 12
    else:
        length_score = 8

    action_score = min(25, action_hits * 4)
    metrics_score = min(20, metric_hits // 2)
    section_score = min(20, section_hits * 4)
    readability_score = 10 if "\n" in cleaned_text else 5

    return min(100, length_score + action_score + metrics_score + section_score + readability_score)


def _compute_jd_match(normalized_resume: str, job_description: str) -> tuple[int | None, List[str]]:
    jd_clean = job_description.strip()
    if not jd_clean:
        return None, []

    jd_keywords = _extract_keywords(jd_clean, min_len=4, top_k=24)
    if not jd_keywords:
        return None, []

    resume_tokens: Set[str] = set(normalized_resume.split())
    matched = [keyword for keyword in jd_keywords if keyword in resume_tokens]
    missing = [keyword for keyword in jd_keywords if keyword not in resume_tokens]
    score = int(round((len(matched) / len(jd_keywords)) * 100))
    return score, missing[:12]


def _section_scores(keyword_coverage: int, ats_score: int, impact_hits: int, jd_match_score: int | None) -> Dict[str, int]:
    relevance = min(100, int(round((keyword_coverage * 0.75) + ((jd_match_score or keyword_coverage) * 0.25))))
    impact = min(100, 30 + impact_hits * 12)
    clarity = min(100, int(round((ats_score * 0.7) + (keyword_coverage * 0.3))))
    ats_compatibility = ats_score
    return {
        "relevance": max(0, relevance),
        "impact": max(0, impact),
        "clarity": max(0, clarity),
        "ats_compatibility": max(0, ats_compatibility),
    }


def _confidence(keyword_coverage: int, ats_score: int, jd_match_score: int | None) -> str:
    composite = int(round((keyword_coverage * 0.5) + (ats_score * 0.35) + ((jd_match_score or keyword_coverage) * 0.15)))
    if composite >= 75:
        return "high"
    if composite >= 50:
        return "medium"
    return "low"


def _build_priority_actions(missing_skills: List[str], section_scores: Dict[str, int], jd_missing: List[str]) -> tuple[List[str], List[str], List[str]]:
    must_fix_now = [f"Show proof for {skill} using outcomes and metrics." for skill in missing_skills[:3]]
    if jd_missing:
        must_fix_now.append(f"Add JD language for: {', '.join(jd_missing[:4])}.")

    improve_next: List[str] = []
    if section_scores.get("impact", 0) < 60:
        improve_next.append("Convert weak statements into action + impact bullets with numbers.")
    if section_scores.get("ats_compatibility", 0) < 65:
        improve_next.append("Use standard headings and simple formatting for ATS parsing.")
    if section_scores.get("relevance", 0) < 65:
        improve_next.append("Prioritize projects aligned with the target role at the top.")

    polish_later = [
        "Shorten long paragraphs into concise bullets.",
        "Keep tense and formatting consistent across sections.",
        "Use stronger role-specific keywords in summary and headline.",
    ]
    return must_fix_now[:4], improve_next[:4], polish_later[:3]


def _rewrite_guidance(cleaned_text: str) -> List[str]:
    raw_lines = [line.strip() for line in cleaned_text.splitlines() if line.strip()]
    suggestions: List[str] = []

    for line in raw_lines[:18]:
        line_lower = line.lower()
        if "responsible for" in line_lower:
            suggestions.append(
                f"Before: {line}\nAfter: Led <scope> by using <skill>, resulting in <measurable outcome>."
            )
        elif len(line.split()) > 18:
            suggestions.append(
                f"Before: {line}\nAfter: Split into 2 bullets focused on action and quantified impact."
            )
        elif "worked on" in line_lower:
            suggestions.append(
                f"Before: {line}\nAfter: Built <feature/system> with <tools>, improving <metric> by <value>."
            )

    if not suggestions:
        suggestions.append(
            "Before: Generic role summary\nAfter: 1-line value proposition with role, years, strongest tools, and top impact metric."
        )
    return suggestions[:6]


def _verdict(score: int, ats_score: int, confidence: str) -> str:
    if score >= 80 and ats_score >= 75 and confidence == "high":
        return "Strong submission: interview-ready with minor tuning."
    if score >= 60:
        return "Promising profile: improve key gaps to become interview-competitive."
    return "Needs repositioning: focus on core role evidence and ATS structure first."


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

    role_match_score = _score_resume(len(matched_skills), len(required_skills), normalized_resume)
    keyword_coverage = int(round((len(matched_skills) / len(required_skills)) * 100)) if required_skills else 0
    ats_score = _compute_ats_score(cleaned_text, normalized_resume)
    jd_match_score, missing_jd_keywords = _compute_jd_match(normalized_resume, resume_input.job_description)

    if jd_match_score is not None:
        score = int(round((role_match_score * 0.6) + (ats_score * 0.25) + (jd_match_score * 0.15)))
    else:
        score = int(round((role_match_score * 0.75) + (ats_score * 0.25)))

    impact_hits = sum(1 for keyword in IMPACT_KEYWORDS if contains_phrase(normalized_resume, keyword))
    section_scores = _section_scores(keyword_coverage, ats_score, impact_hits, jd_match_score)
    confidence_level = _confidence(keyword_coverage, ats_score, jd_match_score)
    target_profile = f"{resume_input.seniority.title()} {role_used.replace('_', ' ').title()}"
    if resume_input.target_title.strip():
        target_profile = resume_input.target_title.strip()

    suggestions = _build_suggestions(missing_skills, score)
    must_fix_now, improve_next, polish_later = _build_priority_actions(
        missing_skills,
        section_scores,
        missing_jd_keywords,
    )
    suggestions = suggestions + must_fix_now + improve_next + polish_later[:2]

    strengths = []
    if matched_skills:
        strengths.append(f"Role-relevant skill evidence found for: {', '.join(matched_skills[:4])}.")
    if impact_hits:
        strengths.append("Impact language is present, which helps recruiter confidence.")
    if ats_score >= 70:
        strengths.append("Resume structure appears ATS-friendly.")
    if jd_match_score is not None and jd_match_score >= 65:
        strengths.append("Job description alignment is strong.")

    risks = []
    if missing_skills:
        risks.append(f"Missing critical role skills: {', '.join(missing_skills[:4])}.")
    if ats_score < 60:
        risks.append("ATS compatibility is low; formatting and clarity may hurt parsing.")
    if jd_match_score is not None and jd_match_score < 50:
        risks.append("Job description alignment is weak; add exact domain keywords.")

    quick_wins = [
        "Rewrite top 3 bullets using action + metric format.",
        "Move most relevant project to the top of Experience.",
        "Mirror important keywords from the target job description.",
    ]
    rewrite_guidance = _rewrite_guidance(cleaned_text)
    narrative_feedback = (
        f"Role match is {score}/100 with ATS {ats_score}/100 and keyword coverage {keyword_coverage}%. "
        "Strengthen missing skills with concrete outcomes and use tighter, metric-driven bullets."
    )
    overall_verdict = _verdict(score, ats_score, confidence_level)

    elapsed_ms = int((time.perf_counter() - start_time) * 1000)
    return AnalysisResult(
        score=score,
        missing_skills=missing_skills,
        suggestions=suggestions,
        role_used=role_used,
        truncated=truncated,
        error=None,
        elapsed_ms=elapsed_ms,
        ats_score=ats_score,
        keyword_coverage=keyword_coverage,
        section_scores=section_scores,
        jd_match_score=jd_match_score,
        missing_jd_keywords=missing_jd_keywords,
        rewrite_guidance=rewrite_guidance,
        strengths=strengths,
        risks=risks,
        quick_wins=quick_wins,
        narrative_feedback=narrative_feedback,
        confidence_level=confidence_level,
        target_profile=target_profile,
        must_fix_now=must_fix_now,
        improve_next=improve_next,
        polish_later=polish_later,
        overall_verdict=overall_verdict,
    )
