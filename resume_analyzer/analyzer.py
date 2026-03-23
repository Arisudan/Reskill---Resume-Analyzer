import time
from typing import Dict, List

from .models import AnalysisResult, ResumeInput
from .skills import ROLE_SKILLS, infer_role_from_title, normalize_role
from .text_utils import contains_phrase, normalize_text, sanitize_and_truncate


IMPACT_KEYWORDS = ["led", "built", "improved", "optimized", "shipped"]
ATS_KEYWORDS = [
    "email", "phone", "linkedin", "github", "experience", "education",
    "skills", "projects", "certification", "languages", "summary", "objective"
]
ATS_SECTION_HEADERS = [
    "experience", "education", "skills", "projects", 
    "certification", "summary", "objective", "languages"
]
SENIORITY_KEYWORDS = {
    "intern": ["intern", "trainee", "student"],
    "junior": ["junior", "associate", "entry"],
    "mid": ["mid", "specialist", "developer"],
    "senior": ["senior", "lead", "architect", "ownership"],
    "manager": ["manager", "director", "strategy", "stakeholder"],
}
INDUSTRY_KEYWORDS = {
    "fintech": ["payments", "compliance", "risk", "transaction"],
    "healthcare": ["hipaa", "ehr", "patient", "clinical"],
    "ecommerce": ["checkout", "catalog", "conversion", "cart"],
    "saas": ["subscription", "retention", "churn", "b2b"],
}
COMMON_STOPWORDS = {
    "the", "and", "for", "with", "from", "that", "this", "your", "have", "will", "you",
    "are", "our", "not", "but", "has", "had", "was", "were", "their", "into", "than",
    "about", "role", "years", "year", "work", "using", "use", "ability", "strong",
}
ACTION_VERBS = {
    "built", "developed", "designed", "implemented", "led", "created", "optimized",
    "automated", "managed", "improved", "reduced", "increased", "delivered", "integrated",
    "deployed", "migrated", "analyzed", "secured", "tested", "engineered", "maintained",
}


def _calculate_ats_score(cleaned_text: str) -> int:
    """Calculate ATS compatibility score (0-100)."""
    normalized = normalize_text(cleaned_text)
    word_list = normalized.split()
    
    ats_score = 30  # Base score
    
    # Check for contact information
    contact_points = 0
    if "email" in normalized or "@" in normalized:
        contact_points += 10
    if "phone" in normalized or any(char.isdigit() for char in normalized[-20:]):
        contact_points += 10
    if "linkedin" in normalized or "github" in normalized:
        contact_points += 10
    ats_score += min(contact_points, 20)
    
    # Check for section headers
    header_points = 0
    for header in ATS_SECTION_HEADERS:
        if contains_phrase(normalized, header):
            header_points += 2
    ats_score += min(header_points, 15)
    
    # Check for keyword presence
    keyword_count = sum(1 for kw in ATS_KEYWORDS if contains_phrase(normalized, kw))
    keyword_score = (keyword_count / len(ATS_KEYWORDS)) * 15
    ats_score += int(keyword_score)
    
    # Check for proper formatting (dates, numbers)
    has_years = any(year in normalized for year in [str(y) for y in range(2010, 2026)])
    has_structure = len(word_list) > 50 and len(word_list) < 1000
    
    if has_years:
        ats_score += 5
    if has_structure:
        ats_score += 5
    
    # Check for impact words (shows quantifiable results)
    impact_count = sum(1 for kw in IMPACT_KEYWORDS if contains_phrase(normalized, kw))
    impact_score = min(impact_count * 3, 10)
    ats_score += impact_score
    
    return min(100, ats_score)


def _extract_keywords(text: str, limit: int = 30) -> List[str]:
    tokens = normalize_text(text).split(" ")
    keywords: List[str] = []
    for token in tokens:
        if len(token) < 4 or token in COMMON_STOPWORDS:
            continue
        if token.isdigit():
            continue
        if token not in keywords:
            keywords.append(token)
        if len(keywords) >= limit:
            break
    return keywords


def _resolve_role(resume_input: ResumeInput) -> str:
    explicit_role = normalize_role(resume_input.role)
    if explicit_role != "default":
        return explicit_role
    inferred = infer_role_from_title(resume_input.target_title)
    return inferred if inferred else "default"


def _validate_input(resume_input: ResumeInput, cleaned_text: str) -> str | None:
    if not cleaned_text:
        return "resume_text is empty"
    if len(cleaned_text) < 5:
        return "resume_text is too short; provide at least 5 characters"
    if len(resume_input.target_title) > 120:
        return "target_title is too long"
    if len(resume_input.industry) > 80:
        return "industry is too long"
    if len(resume_input.job_description) > 30000:
        return "job_description is too long"
    return None


def _section_scores(cleaned_text: str, role_used: str) -> Dict[str, int]:
    normalized = normalize_text(cleaned_text)

    def score_section(section_name: str, min_words: int, expected_keywords: List[str]) -> int:
        header_present = 40 if contains_phrase(normalized, section_name) else 15
        word_count = len(cleaned_text.split())
        depth = min(35, int((word_count / max(min_words, 1)) * 35))
        keyword_hits = sum(1 for kw in expected_keywords if contains_phrase(normalized, kw))
        relevance = min(25, keyword_hits * 5)
        return min(100, header_present + depth + relevance)

    role_keywords = ROLE_SKILLS.get(role_used, ROLE_SKILLS["default"])
    return {
        "summary": score_section("summary", 35, role_keywords[:2]),
        "experience": score_section("experience", 120, role_keywords[:4]),
        "projects": score_section("projects", 60, role_keywords[:3]),
        "skills": score_section("skills", 20, role_keywords),
        "education": score_section("education", 30, ["degree", "university", "certification"]),
    }


def _jd_match(normalized_resume: str, job_description: str) -> tuple[int | None, List[str]]:
    if not job_description.strip():
        return None, []

    jd_keywords = _extract_keywords(job_description, limit=40)
    if not jd_keywords:
        return 0, []

    matched = [kw for kw in jd_keywords if contains_phrase(normalized_resume, kw)]
    missing = [kw for kw in jd_keywords if kw not in matched]
    score = int(round((len(matched) / len(jd_keywords)) * 100))
    return score, missing[:12]


def _target_profile(resume_input: ResumeInput, role_used: str) -> str:
    title = resume_input.target_title.strip() or role_used.replace("_", " ").title()
    seniority = resume_input.seniority.strip() or "Not specified"
    industry = resume_input.industry.strip() or "General"
    return f"Title: {title} | Seniority: {seniority} | Industry: {industry}"


def _keyword_coverage(normalized_resume: str, role_used: str, resume_input: ResumeInput) -> int:
    target_keywords = list(ROLE_SKILLS.get(role_used, ROLE_SKILLS["default"]))

    seniority_key = resume_input.seniority.strip().lower()
    if seniority_key in SENIORITY_KEYWORDS:
        target_keywords.extend(SENIORITY_KEYWORDS[seniority_key])

    industry_key = resume_input.industry.strip().lower()
    if industry_key in INDUSTRY_KEYWORDS:
        target_keywords.extend(INDUSTRY_KEYWORDS[industry_key])

    title_tokens = [t for t in normalize_text(resume_input.target_title).split(" ") if len(t) > 2]
    target_keywords.extend(title_tokens[:6])

    deduped = []
    for kw in target_keywords:
        if kw and kw not in deduped:
            deduped.append(kw)

    if not deduped:
        return 0

    matched = sum(1 for kw in deduped if contains_phrase(normalized_resume, kw))
    return int(round((matched / len(deduped)) * 100))


def _build_fact_preserving_rewrites(cleaned_text: str, missing_skills: List[str]) -> List[str]:
    lines = [line.strip(" -*\t") for line in cleaned_text.splitlines() if line.strip()]

    def is_actionable(line: str) -> bool:
        lower = line.lower().strip()
        if len(lower) < 35:
            return False
        if "@" in lower or lower.startswith("http") or "www." in lower:
            return False
        words = lower.split()
        if len(words) <= 6 and lower.upper() == line.strip():
            return False
        if sum(1 for ch in lower if ch.isalpha()) < 20:
            return False
        return any(verb in lower for verb in ACTION_VERBS)

    candidate_lines = [line for line in lines if is_actionable(line)][:3]
    rewrites: List[str] = []

    for idx, line in enumerate(candidate_lines, start=1):
        skill_hint = missing_skills[idx - 1] if idx - 1 < len(missing_skills) else "relevant skill"
        concise = " ".join(line.split())
        rewrites.append(
            "Original bullet: "
            + concise
            + "\n"
            + "Rewrite structure: Action + Scope + Tools + Measurable Result"
            + "\n"
            + "Improved bullet (fact-preserving template): "
            + concise
            + f" Used {skill_hint} for <specific scope>, resulting in <quantified outcome>."
        )

    if not rewrites:
        rewrites.extend(
            [
                "Start each experience bullet with a strong action verb and include the project or ownership scope.",
                "Add one tool/technology already present in your resume and end with a measurable impact (%, time, cost, quality).",
                "Template: <Action> <what you built/changed> using <tool/skill>, improving <metric> by <value>.",
            ]
        )

    return rewrites


def _build_strengths(
    matched_skills: List[str],
    ats_score: int,
    section_scores: Dict[str, int],
    jd_match_score: int | None,
) -> List[str]:
    strengths: List[str] = []
    if matched_skills:
        strengths.append(f"Matched {len(matched_skills)} core role skills: {', '.join(matched_skills[:4])}.")
    if ats_score >= 75:
        strengths.append("Strong ATS readiness with good structure and scanability.")
    top_sections = [name for name, score in section_scores.items() if score >= 80]
    if top_sections:
        strengths.append(f"High-performing sections: {', '.join(s.title() for s in top_sections)}.")
    if jd_match_score is not None and jd_match_score >= 70:
        strengths.append("Good alignment with the provided job description.")
    if not strengths:
        strengths.append("You have baseline alignment; targeted improvements can quickly increase impact.")
    return strengths


def _build_risks(
    score: int,
    ats_score: int,
    keyword_coverage: int,
    section_scores: Dict[str, int],
    missing_skills: List[str],
    missing_jd_keywords: List[str],
) -> List[str]:
    risks: List[str] = []
    if score < 55:
        risks.append("Role fit is currently moderate/low; shortlist probability may drop for competitive roles.")
    if ats_score < 60:
        risks.append("ATS compatibility risk: missing structure and keyword signals could reduce visibility.")
    if keyword_coverage < 50:
        risks.append("Low target-keyword coverage may hurt recruiter and ATS relevance ranking.")

    weak_sections = [name for name, section_score in section_scores.items() if section_score < 55]
    if weak_sections:
        risks.append("Weak sections detected: " + ", ".join(s.title() for s in weak_sections) + ".")

    if missing_skills:
        risks.append("Missing role skills: " + ", ".join(missing_skills[:4]) + ".")
    if missing_jd_keywords:
        risks.append("Missing JD terms: " + ", ".join(missing_jd_keywords[:4]) + ".")

    if not risks:
        risks.append("No major risks detected; continue optimizing outcomes and specificity.")
    return risks


def _build_quick_wins(missing_skills: List[str], missing_jd_keywords: List[str], section_scores: Dict[str, int]) -> List[str]:
    wins: List[str] = []
    for skill in missing_skills[:3]:
        wins.append(f"Add one quantified bullet showing {skill} usage in a real project.")
    for keyword in missing_jd_keywords[:3]:
        wins.append(f"Include '{keyword}' naturally in Summary or Experience where truthful.")

    weakest = min(section_scores, key=section_scores.get)
    wins.append(f"Upgrade the {weakest.title()} section first; this will improve overall score fastest.")
    return wins[:6]


def _confidence_level(score: int, ats_score: int, keyword_coverage: int, jd_match_score: int | None) -> str:
    jd_component = jd_match_score if jd_match_score is not None else 60
    composite = int(round((score * 0.35) + (ats_score * 0.25) + (keyword_coverage * 0.2) + (jd_component * 0.2)))
    if composite >= 80:
        return "high"
    if composite >= 60:
        return "medium"
    return "low"


def _narrative_feedback(
    score: int,
    ats_score: int,
    keyword_coverage: int,
    jd_match_score: int | None,
    weakest_section: str,
) -> str:
    jd_text = f"JD match is {jd_match_score}/100" if jd_match_score is not None else "JD match not provided"
    return (
        f"Current profile health: role match {score}/100, ATS {ats_score}/100, "
        f"keyword coverage {keyword_coverage}%. {jd_text}. "
        f"Your biggest improvement opportunity right now is the {weakest_section.title()} section."
    )


def _match_skills(normalized_resume: str, required_skills: List[str]) -> List[str]:
    return [skill for skill in required_skills if contains_phrase(normalized_resume, skill)]


def _score_resume(matched_count: int, required_count: int, normalized_resume: str) -> int:
    base = 20
    coverage_component = int(round((matched_count / required_count) * 70)) if required_count else 0
    impact_hits = sum(1 for keyword in IMPACT_KEYWORDS if contains_phrase(normalized_resume, keyword))
    impact_component = min(10, impact_hits * 2)
    return min(100, base + coverage_component + impact_component)


def _build_suggestions(
    missing_skills: List[str],
    score: int,
    ats_score: int,
    keyword_coverage: int,
    section_scores: Dict[str, int],
    resume_input: ResumeInput,
    jd_match_score: int | None,
    missing_jd_keywords: List[str],
) -> List[str]:
    suggestions = [f"Add evidence of {skill} with a concrete project or impact metric." for skill in missing_skills[:5]]
    if score < 50:
        suggestions.append("Strengthen role alignment by highlighting direct, recent experience.")
    if ats_score < 60:
        suggestions.append("Improve ATS compatibility: Add clear section headers (Experience, Education, Skills).")
    if keyword_coverage < 55:
        suggestions.append("Increase keyword alignment for the target role with role-specific terminology in Summary and Experience.")

    if jd_match_score is not None and jd_match_score < 60:
        suggestions.append("Improve job-description alignment by incorporating the top missing JD keywords in your Summary and Experience bullets.")
    if missing_jd_keywords:
        suggestions.append("Prioritize these JD gaps first: " + ", ".join(missing_jd_keywords[:5]))

    weakest = min(section_scores, key=section_scores.get)
    if section_scores[weakest] < 60:
        suggestions.append(f"Improve your {weakest.title()} section with more role-relevant, measurable outcomes.")

    if resume_input.seniority.strip().lower() in ("senior", "manager"):
        suggestions.append("Add leadership and scope metrics (team size, ownership area, business impact) for senior-level targeting.")

    if resume_input.industry.strip():
        suggestions.append(
            f"Add {resume_input.industry.strip()} domain keywords to improve role-context matching for recruiters."
        )

    if not suggestions:
        suggestions.append("Resume aligns well. Improve clarity with quantified outcomes per project.")
    return suggestions


def _error_result(resume_input: ResumeInput, truncated: bool, message: str, elapsed_ms: int) -> AnalysisResult:
    role_used = _resolve_role(resume_input)
    return AnalysisResult(
        score=None,
        ats_score=None,
        keyword_coverage=None,
        section_scores={},
        jd_match_score=None,
        missing_jd_keywords=[],
        rewrite_guidance=[],
        strengths=[],
        risks=[],
        quick_wins=[],
        narrative_feedback="",
        confidence_level="low",
        missing_skills=[],
        suggestions=[],
        role_used=role_used,
        target_profile=_target_profile(resume_input, role_used),
        truncated=truncated,
        error=message,
        elapsed_ms=elapsed_ms,
    )


def analyze_resume(resume_input: ResumeInput) -> AnalysisResult:
    start_time = time.perf_counter()
    cleaned_text, truncated = sanitize_and_truncate(resume_input.resume_text)

    try:
        validation_error = _validate_input(resume_input, cleaned_text)
        if validation_error:
            elapsed_ms = int((time.perf_counter() - start_time) * 1000)
            return _error_result(resume_input, truncated, validation_error, elapsed_ms)

        role_used = _resolve_role(resume_input)
        required_skills = ROLE_SKILLS[role_used]
        normalized_resume = normalize_text(cleaned_text)

        ats_score = _calculate_ats_score(cleaned_text)
        keyword_coverage = _keyword_coverage(normalized_resume, role_used, resume_input)
        section_scores = _section_scores(cleaned_text, role_used)
        jd_match_score, missing_jd_keywords = _jd_match(normalized_resume, resume_input.job_description)

        matched_skills = _match_skills(normalized_resume, required_skills)
        missing_skills = [skill for skill in required_skills if skill not in matched_skills]

        score = _score_resume(len(matched_skills), len(required_skills), normalized_resume)
        rewrite_guidance = _build_fact_preserving_rewrites(cleaned_text, missing_skills)
        strengths = _build_strengths(matched_skills, ats_score, section_scores, jd_match_score)
        risks = _build_risks(
            score,
            ats_score,
            keyword_coverage,
            section_scores,
            missing_skills,
            missing_jd_keywords,
        )
        quick_wins = _build_quick_wins(missing_skills, missing_jd_keywords, section_scores)
        weakest_section = min(section_scores, key=section_scores.get)
        confidence_level = _confidence_level(score, ats_score, keyword_coverage, jd_match_score)
        narrative_feedback = _narrative_feedback(
            score,
            ats_score,
            keyword_coverage,
            jd_match_score,
            weakest_section,
        )
        suggestions = _build_suggestions(
            missing_skills,
            score,
            ats_score,
            keyword_coverage,
            section_scores,
            resume_input,
            jd_match_score,
            missing_jd_keywords,
        )

        elapsed_ms = int((time.perf_counter() - start_time) * 1000)
        return AnalysisResult(
            score=score,
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
            missing_skills=missing_skills,
            suggestions=suggestions,
            role_used=role_used,
            target_profile=_target_profile(resume_input, role_used),
            truncated=truncated,
            error=None,
            elapsed_ms=elapsed_ms,
        )
    except Exception:
        elapsed_ms = int((time.perf_counter() - start_time) * 1000)
        # Fallback behavior: safe deterministic error payload instead of runtime crash.
        return _error_result(
            resume_input,
            truncated,
            "analysis temporarily unavailable; fallback mode active",
            elapsed_ms,
        )
