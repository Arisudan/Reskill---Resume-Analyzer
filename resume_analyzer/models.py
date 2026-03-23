from dataclasses import dataclass
from typing import List, Optional


@dataclass(frozen=True)
class ResumeInput:
    role: str
    resume_text: str


@dataclass(frozen=True)
class AnalysisResult:
    score: Optional[int]
    missing_skills: List[str]
    suggestions: List[str]
    role_used: str
    truncated: bool
    error: Optional[str]
    elapsed_ms: int
