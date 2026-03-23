from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass(frozen=True)
class ResumeInput:
    role: str
    resume_text: str
    target_title: str = ""
    seniority: str = "mid"
    industry: str = ""
    job_description: str = ""


@dataclass(frozen=True)
class AnalysisResult:
    score: Optional[int]
    missing_skills: List[str]
    suggestions: List[str]
    role_used: str
    truncated: bool
    error: Optional[str]
    elapsed_ms: int
    ats_score: int = 0
    keyword_coverage: int = 0
    section_scores: Dict[str, int] = field(default_factory=dict)
    jd_match_score: Optional[int] = None
    missing_jd_keywords: List[str] = field(default_factory=list)
    rewrite_guidance: List[str] = field(default_factory=list)
    strengths: List[str] = field(default_factory=list)
    risks: List[str] = field(default_factory=list)
    quick_wins: List[str] = field(default_factory=list)
    narrative_feedback: str = ""
    confidence_level: str = "medium"
    target_profile: str = "General Role"
    must_fix_now: List[str] = field(default_factory=list)
    improve_next: List[str] = field(default_factory=list)
    polish_later: List[str] = field(default_factory=list)
    overall_verdict: str = ""
