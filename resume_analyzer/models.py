from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass(frozen=True)
class ResumeInput:
    role: str
    resume_text: str
    target_title: str = ""
    seniority: str = ""
    industry: str = ""
    job_description: str = ""


@dataclass(frozen=True)
class AnalysisResult:
    score: Optional[int]
    ats_score: Optional[int]
    keyword_coverage: Optional[int]
    section_scores: Dict[str, int]
    jd_match_score: Optional[int]
    missing_jd_keywords: List[str]
    rewrite_guidance: List[str]
    strengths: List[str]
    risks: List[str]
    quick_wins: List[str]
    narrative_feedback: str
    confidence_level: str
    missing_skills: List[str]
    suggestions: List[str]
    role_used: str
    target_profile: str
    truncated: bool
    error: Optional[str]
    elapsed_ms: int
