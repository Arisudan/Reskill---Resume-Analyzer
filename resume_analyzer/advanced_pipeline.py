from __future__ import annotations

import io
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from .skills import ROLE_SKILLS
from .text_utils import normalize_text


SECTION_PATTERNS = {
    "summary": re.compile(r"\b(summary|profile|about me|professional summary)\b", re.IGNORECASE),
    "experience": re.compile(r"\b(experience|employment|work history|professional experience)\b", re.IGNORECASE),
    "education": re.compile(r"\b(education|academic|qualification)\b", re.IGNORECASE),
    "skills": re.compile(r"\b(skills|technical skills|core skills|technologies)\b", re.IGNORECASE),
    "projects": re.compile(r"\b(projects|project experience|key projects)\b", re.IGNORECASE),
    "certifications": re.compile(r"\b(certifications|licenses|courses)\b", re.IGNORECASE),
}

WEAK_VERBS = {
    "helped",
    "assisted",
    "worked",
    "involved",
    "participated",
    "responsible",
    "supported",
}

STRONG_VERBS = {
    "led",
    "built",
    "implemented",
    "designed",
    "optimized",
    "shipped",
    "launched",
    "delivered",
    "automated",
}

SKILL_ALIAS = {
    "js": "javascript",
    "node": "node.js",
    "py": "python",
    "ml": "machine learning",
    "nlp": "natural language processing",
    "reactjs": "react",
    "rest": "apis",
}


@dataclass
class ParsedResume:
    text: str
    source: str
    parse_notes: List[str]


@dataclass
class ExtractedSignals:
    sections: Dict[str, str]
    matched_skills: List[str]
    missing_skills: List[str]
    weak_bullets: List[str]
    strong_bullets: List[str]
    bullets_with_metrics: int
    bullets_without_metrics: int
    contact_completeness: Dict[str, bool]
    ats_flags: List[str]
    jd_similarity: Optional[int]


@dataclass
class WeightedScore:
    total: int
    components: Dict[str, int]


def _safe_import_pdfplumber():
    try:
        import pdfplumber  # type: ignore

        return pdfplumber
    except Exception:
        return None


def _safe_import_fitz():
    try:
        import fitz  # type: ignore

        return fitz
    except Exception:
        return None


def _safe_import_pytesseract():
    try:
        import pytesseract  # type: ignore

        return pytesseract
    except Exception:
        return None


def _safe_import_spacy():
    try:
        import spacy  # type: ignore

        return spacy
    except Exception:
        return None


def _safe_import_rapidfuzz():
    try:
        from rapidfuzz import fuzz  # type: ignore

        return fuzz
    except Exception:
        return None


def _safe_import_sklearn():
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer  # type: ignore
        from sklearn.metrics.pairwise import cosine_similarity  # type: ignore

        return TfidfVectorizer, cosine_similarity
    except Exception:
        return None, None


def parse_resume_file(filename: str, raw_bytes: bytes) -> ParsedResume:
    lower = filename.lower()
    notes: List[str] = []

    if lower.endswith(".txt"):
        try:
            return ParsedResume(text=raw_bytes.decode("utf-8"), source="txt", parse_notes=notes)
        except UnicodeDecodeError:
            return ParsedResume(text=raw_bytes.decode("latin-1", errors="ignore"), source="txt", parse_notes=notes)

    if lower.endswith(".docx"):
        try:
            from docx import Document  # type: ignore

            document = Document(io.BytesIO(raw_bytes))
            text = "\n".join(p.text for p in document.paragraphs).strip()
            return ParsedResume(text=text, source="docx", parse_notes=notes)
        except Exception as exc:
            notes.append(f"DOCX parse issue: {exc}")

    if lower.endswith(".pdf"):
        pdfplumber = _safe_import_pdfplumber()
        if pdfplumber is not None:
            try:
                chunks: List[str] = []
                with pdfplumber.open(io.BytesIO(raw_bytes)) as pdf:
                    for page in pdf.pages:
                        chunks.append(page.extract_text() or "")
                text = "\n".join(chunks).strip()
                if text:
                    notes.append("PDF parsed with pdfplumber")
                    return ParsedResume(text=text, source="pdfplumber", parse_notes=notes)
            except Exception as exc:
                notes.append(f"pdfplumber fallback triggered: {exc}")

        fitz = _safe_import_fitz()
        if fitz is not None:
            try:
                doc = fitz.open(stream=raw_bytes, filetype="pdf")
                chunks: List[str] = []
                for page in doc:
                    chunks.append(page.get_text("text"))
                text = "\n".join(chunks).strip()
                if text:
                    notes.append("PDF parsed with PyMuPDF")
                    return ParsedResume(text=text, source="pymupdf", parse_notes=notes)

                pytesseract = _safe_import_pytesseract()
                if pytesseract is not None:
                    ocr_chunks: List[str] = []
                    for page in doc:
                        pix = page.get_pixmap()
                        from PIL import Image  # type: ignore

                        image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                        ocr_chunks.append(pytesseract.image_to_string(image))
                    ocr_text = "\n".join(ocr_chunks).strip()
                    if ocr_text:
                        notes.append("OCR used via pytesseract")
                        return ParsedResume(text=ocr_text, source="ocr", parse_notes=notes)
            except Exception as exc:
                notes.append(f"PyMuPDF/OCR fallback issue: {exc}")

    return ParsedResume(text="", source="unknown", parse_notes=notes)


def detect_sections(text: str) -> Dict[str, str]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    sections = {name: "" for name in SECTION_PATTERNS.keys()}
    current = "summary"

    for line in lines:
        switched = False
        for section_name, pattern in SECTION_PATTERNS.items():
            if pattern.search(line):
                current = section_name
                switched = True
                break
        if switched:
            continue
        sections[current] += (line + "\n")

    return {k: v.strip() for k, v in sections.items()}


def _spacy_skill_candidates(text: str) -> List[str]:
    spacy_mod = _safe_import_spacy()
    if spacy_mod is None:
        return []

    try:
        nlp = spacy_mod.blank("en")
        doc = nlp(text)
        candidates = [token.text.lower() for token in doc if token.is_alpha and len(token.text) >= 2]
        return candidates
    except Exception:
        return []


def extract_skills(text: str, role_used: str) -> Tuple[List[str], List[str]]:
    normalized = normalize_text(text)
    tokens = set(normalized.split())
    candidates = set(_spacy_skill_candidates(text)) | tokens

    required_skills = ROLE_SKILLS.get(role_used, ROLE_SKILLS["default"])
    matched: List[str] = []

    fuzz = _safe_import_rapidfuzz()

    for skill in required_skills:
        if skill in normalized:
            matched.append(skill)
            continue

        aliases = [k for k, v in SKILL_ALIAS.items() if v == skill] + [skill]
        if any(alias in candidates for alias in aliases):
            matched.append(skill)
            continue

        if fuzz is not None:
            for token in list(candidates)[:400]:
                if fuzz.ratio(skill, token) >= 85:
                    matched.append(skill)
                    break

    matched = sorted(set(matched), key=lambda x: required_skills.index(x) if x in required_skills else 999)
    missing = [skill for skill in required_skills if skill not in matched]
    return matched, missing


def bullet_strength(text: str) -> Tuple[List[str], List[str], int, int]:
    raw_lines = [line.strip() for line in text.splitlines() if line.strip()]
    bullet_lines = [line for line in raw_lines if line.startswith(("-", "*", "•")) or len(line.split()) > 6]

    weak: List[str] = []
    strong: List[str] = []
    with_numbers = 0
    without_numbers = 0

    for line in bullet_lines[:60]:
        plain = line.lstrip("-*• ").strip()
        lower = plain.lower()

        has_number = bool(re.search(r"\b\d+(%|x|k|m|\+)?\b", plain))
        if has_number:
            with_numbers += 1
        else:
            without_numbers += 1

        if any(verb in lower for verb in WEAK_VERBS):
            weak.append(plain)
        if any(verb in lower for verb in STRONG_VERBS) and has_number:
            strong.append(plain)

    return weak[:8], strong[:8], with_numbers, without_numbers


def contact_completeness(text: str) -> Dict[str, bool]:
    checks = {
        "email": bool(re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)),
        "phone": bool(re.search(r"(\+?\d[\d\-\s]{8,}\d)", text)),
        "linkedin": "linkedin.com" in text.lower(),
        "github": "github.com" in text.lower(),
    }
    return checks


def ats_compatibility_flags(text: str) -> List[str]:
    flags: List[str] = []
    if "|" in text:
        flags.append("Possible table-like formatting detected.")
    if re.search(r"\b(image|icon|graphic|logo)\b", text.lower()):
        flags.append("Possible image-heavy content can confuse ATS.")

    standard_headers = ["summary", "experience", "education", "skills"]
    lowered = text.lower()
    missing_headers = [header for header in standard_headers if header not in lowered]
    if missing_headers:
        flags.append("Missing some standard section headers: " + ", ".join(missing_headers))

    if re.search(r"[^\x00-\x7F]", text):
        flags.append("Special characters detected; ATS parsers may misread some symbols.")

    return flags


def jd_similarity_score(resume_text: str, job_description: str) -> Optional[int]:
    if not job_description.strip():
        return None

    TfidfVectorizer, cosine_similarity = _safe_import_sklearn()
    if TfidfVectorizer is None or cosine_similarity is None:
        return None

    try:
        vectorizer = TfidfVectorizer(stop_words="english")
        matrix = vectorizer.fit_transform([resume_text, job_description])
        score = cosine_similarity(matrix[0:1], matrix[1:2])[0][0]
        return int(round(score * 100))
    except Exception:
        return None


def weighted_resume_score(
    contact: Dict[str, bool],
    sections: Dict[str, str],
    matched_skills: List[str],
    missing_skills: List[str],
    weak_count: int,
    with_metrics: int,
    ats_flags: List[str],
    jd_similarity: Optional[int],
) -> WeightedScore:
    contact_score = int(round((sum(1 for v in contact.values() if v) / max(1, len(contact))) * 10))

    summary_score = 8 if len(sections.get("summary", "").split()) >= 25 else 4
    exp_score = min(20, 8 + with_metrics * 2 - weak_count)
    edu_score = 10 if sections.get("education") else 4
    skills_score = int(round((len(matched_skills) / max(1, len(matched_skills) + len(missing_skills))) * 20))
    projects_score = 10 if sections.get("projects") else 4
    cert_score = 8 if sections.get("certifications") else 3
    formatting_score = max(0, 14 - len(ats_flags) * 3)
    jd_score = int(round((jd_similarity or 0) * 0.10))

    components = {
        "contact": max(0, min(10, contact_score)),
        "summary": max(0, min(10, summary_score)),
        "experience": max(0, min(20, exp_score)),
        "education": max(0, min(10, edu_score)),
        "skills": max(0, min(20, skills_score)),
        "projects": max(0, min(10, projects_score)),
        "certifications": max(0, min(8, cert_score)),
        "formatting": max(0, min(12, formatting_score)),
        "jd_match": max(0, min(10, jd_score)),
    }

    total = min(100, max(0, sum(components.values())))
    return WeightedScore(total=total, components=components)


def analyze_advanced_signals(text: str, role_used: str, job_description: str) -> ExtractedSignals:
    sections = detect_sections(text)
    matched_skills, missing_skills = extract_skills(text, role_used)
    weak_bullets, strong_bullets, with_metrics, without_metrics = bullet_strength(text)
    contact = contact_completeness(text)
    ats_flags = ats_compatibility_flags(text)
    jd_similarity = jd_similarity_score(text, job_description)

    return ExtractedSignals(
        sections=sections,
        matched_skills=matched_skills,
        missing_skills=missing_skills,
        weak_bullets=weak_bullets,
        strong_bullets=strong_bullets,
        bullets_with_metrics=with_metrics,
        bullets_without_metrics=without_metrics,
        contact_completeness=contact,
        ats_flags=ats_flags,
        jd_similarity=jd_similarity,
    )


def map_courses_for_skills(missing_skills: List[str]) -> List[Dict[str, str]]:
    catalog = {
        "python": ("Python for Everybody", "Coursera", "https://www.coursera.org/specializations/python"),
        "sql": ("SQL for Data Science", "Coursera", "https://www.coursera.org/learn/sql-for-data-science"),
        "docker": ("Docker Crash Course", "YouTube", "https://www.youtube.com/results?search_query=docker+crash+course"),
        "testing": ("Automated Testing in Python", "Udemy", "https://www.udemy.com/topic/pytest/"),
        "javascript": ("JavaScript - The Complete Guide", "Udemy", "https://www.udemy.com/course/javascript-the-complete-guide-2020-beginner-advanced/"),
        "react": ("React Official Tutorial", "React Docs", "https://react.dev/learn"),
        "machine learning": ("Machine Learning Specialization", "Coursera", "https://www.coursera.org/specializations/machine-learning-introduction"),
        "data visualization": ("Data Visualization with Python", "Coursera", "https://www.coursera.org/learn/python-for-data-visualization"),
    }

    recommendations: List[Dict[str, str]] = []
    for skill in missing_skills[:6]:
        title, platform, url = catalog.get(
            skill,
            (
                f"Learn {skill.title()} Fundamentals",
                "YouTube",
                f"https://www.youtube.com/results?search_query={skill.replace(' ', '+')}+tutorial",
            ),
        )
        recommendations.append({
            "skill": skill,
            "title": title,
            "platform": platform,
            "url": url,
        })
    return recommendations


def suggest_jobs(role_used: str, industry: str) -> List[Dict[str, str]]:
    role_label = role_used.replace("_", " ").title()
    industry_q = industry.strip() or "technology"
    links = [
        {
            "title": f"{role_label} roles on LinkedIn",
            "platform": "LinkedIn",
            "url": f"https://www.linkedin.com/jobs/search/?keywords={role_label.replace(' ', '%20')}%20{industry_q.replace(' ', '%20')}",
        },
        {
            "title": f"{role_label} jobs on Indeed",
            "platform": "Indeed",
            "url": f"https://www.indeed.com/jobs?q={role_label.replace(' ', '+')}+{industry_q.replace(' ', '+')}",
        },
        {
            "title": f"Remote {role_label} jobs",
            "platform": "Wellfound",
            "url": f"https://wellfound.com/jobs?query={role_label.replace(' ', '%20')}",
        },
    ]
    return links


def build_highlighted_html(text: str, matched_skills: List[str], missing_skills: List[str]) -> str:
    safe_text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    for skill in sorted(set(matched_skills), key=len, reverse=True):
        if not skill:
            continue
        pattern = re.compile(rf"\b{re.escape(skill)}\b", re.IGNORECASE)
        safe_text = pattern.sub(lambda m: f"<span style='background:#0D1F14;color:#3FB950;padding:1px 4px;border-radius:4px;'>{m.group(0)}</span>", safe_text)

    for skill in sorted(set(missing_skills), key=len, reverse=True):
        if not skill:
            continue
        token = skill.split()[0]
        pattern = re.compile(rf"\b{re.escape(token)}\b", re.IGNORECASE)
        safe_text = pattern.sub(lambda m: f"<span style='background:#2F2411;color:#E3B341;padding:1px 4px;border-radius:4px;'>{m.group(0)}</span>", safe_text)

    html = (
        "<div style='max-height:260px;overflow:auto;border:1px solid #30363D;border-radius:10px;"
        "padding:12px;background:#0f1522;line-height:1.6;font-size:12px;white-space:pre-wrap;'>"
        + safe_text
        + "</div>"
    )
    return html
