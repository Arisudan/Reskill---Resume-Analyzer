"""Streamlit UI for Resume Analyzer with ATS scoring and file upload."""

from __future__ import annotations

import json
from io import BytesIO
from typing import Dict, List

import streamlit as st
from docx import Document
from PyPDF2 import PdfReader
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas

from resume_analyzer.analyzer import analyze_resume
from resume_analyzer.models import ResumeInput
from resume_analyzer.skills import ROLE_SKILLS


ROLE_OPTIONS: Dict[str, str] = {
    "backend_developer": "Backend Developer",
    "frontend_developer": "Frontend Developer",
    "data_scientist": "Data Scientist",
    "default": "General Role",
}
SENIORITY_OPTIONS = ["intern", "junior", "mid", "senior", "manager"]


def _extract_text_from_uploaded_file(uploaded_file) -> str:
    name = uploaded_file.name.lower()
    raw = uploaded_file.read()

    if name.endswith(".txt"):
        try:
            return raw.decode("utf-8")
        except UnicodeDecodeError:
            return raw.decode("latin-1", errors="ignore")

    if name.endswith(".pdf"):
        reader = PdfReader(BytesIO(raw))
        chunks: List[str] = []
        for page in reader.pages:
            chunks.append(page.extract_text() or "")
        return "\n".join(chunks).strip()

    if name.endswith(".docx"):
        document = Document(BytesIO(raw))
        return "\n".join(p.text for p in document.paragraphs).strip()

    return ""


def _score_badge(score: int | None) -> str:
    if score is None:
        return "N/A"
    if score >= 80:
        return "Excellent"
    if score >= 60:
        return "Good"
    if score >= 40:
        return "Fair"
    return "Needs Work"


def _build_pdf_report(payload: Dict) -> bytes:
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    margin = 32
    content_width = width - (2 * margin)
    y = height - margin

    palette = {
        "brand": colors.HexColor("#1A4EA8"),
        "brand_dark": colors.HexColor("#113066"),
        "accent": colors.HexColor("#2F7DF5"),
        "success": colors.HexColor("#1FBCA3"),
        "danger": colors.HexColor("#D94F70"),
        "text": colors.HexColor("#1B2A4A"),
        "muted": colors.HexColor("#5E7397"),
        "border": colors.HexColor("#D6E0F1"),
        "card_bg": colors.HexColor("#F6F9FF"),
    }

    def ensure_space(required: float) -> None:
        nonlocal y
        if y - required < margin:
            pdf.showPage()
            y = height - margin

    def wrap_text(text: str, font_name: str, font_size: float, max_width: float) -> List[str]:
        words = str(text).split()
        if not words:
            return [""]
        lines: List[str] = []
        current = words[0]
        for word in words[1:]:
            candidate = f"{current} {word}"
            if stringWidth(candidate, font_name, font_size) <= max_width:
                current = candidate
            else:
                lines.append(current)
                current = word
        lines.append(current)
        return lines

    def draw_header() -> None:
        nonlocal y
        header_h = 74
        ensure_space(header_h + 10)
        pdf.setFillColor(palette["brand"])
        pdf.roundRect(margin, y - header_h, content_width, header_h, 10, fill=1, stroke=0)

        pdf.setFillColor(colors.white)
        pdf.setFont("Helvetica-Bold", 16)
        pdf.drawString(margin + 14, y - 24, "Reskill - AI based Resume Analyzer")
        pdf.setFont("Helvetica", 10)
        pdf.drawString(margin + 14, y - 42, "Professional Resume Analysis Report")
        pdf.setFont("Helvetica", 8)
        pdf.drawString(margin + 14, y - 56, f"Role: {payload.get('role_used', 'N/A')} | Confidence: {str(payload.get('confidence_level', 'n/a')).upper()}")

        y -= header_h + 12

    def draw_score_cards() -> None:
        nonlocal y
        card_h = 56
        gap = 10
        labels = [
            ("Role Match", f"{payload.get('score', 'N/A')}/100"),
            ("ATS Score", f"{payload.get('ats_score', 'N/A')}/100"),
            ("Keywords", f"{payload.get('keyword_coverage', 'N/A')}%"),
            ("JD Match", f"{payload.get('jd_match_score', 'N/A') if payload.get('jd_match_score') is not None else 'N/A'}"),
        ]
        card_w = (content_width - (3 * gap)) / 4.0
        ensure_space(card_h + 12)

        for i, (title, value) in enumerate(labels):
            x = margin + i * (card_w + gap)
            pdf.setFillColor(palette["card_bg"])
            pdf.setStrokeColor(palette["border"])
            pdf.roundRect(x, y - card_h, card_w, card_h, 8, fill=1, stroke=1)
            pdf.setFillColor(palette["muted"])
            pdf.setFont("Helvetica", 8)
            pdf.drawString(x + 8, y - 16, title)
            pdf.setFillColor(palette["brand_dark"])
            pdf.setFont("Helvetica-Bold", 12)
            pdf.drawString(x + 8, y - 34, str(value))

        y -= card_h + 14

    def draw_section(title: str, lines: List[str], tone: str = "default") -> None:
        nonlocal y
        if not lines:
            return

        heading_color = palette["brand_dark"]
        bullet_color = palette["text"]
        if tone == "success":
            heading_color = palette["success"]
        elif tone == "danger":
            heading_color = palette["danger"]

        ensure_space(28)
        pdf.setFillColor(heading_color)
        pdf.setFont("Helvetica-Bold", 11)
        pdf.drawString(margin, y, title)
        y -= 12

        pdf.setStrokeColor(palette["border"])
        pdf.line(margin, y, margin + content_width, y)
        y -= 10

        for item in lines:
            wrapped = wrap_text(str(item), "Helvetica", 9, content_width - 18)
            required = (len(wrapped) * 12) + 6
            ensure_space(required)

            pdf.setFillColor(heading_color)
            pdf.circle(margin + 4, y - 4, 1.7, fill=1, stroke=0)

            pdf.setFillColor(bullet_color)
            pdf.setFont("Helvetica", 9)
            line_y = y
            for line in wrapped:
                pdf.drawString(margin + 12, line_y, line)
                line_y -= 12

            y = line_y - 2

        y -= 6

    def draw_paragraph_block(title: str, text: str) -> None:
        nonlocal y
        wrapped = wrap_text(text, "Helvetica", 9, content_width - 18)
        block_h = max(40, 20 + len(wrapped) * 12)
        ensure_space(block_h + 12)

        pdf.setFillColor(palette["card_bg"])
        pdf.setStrokeColor(palette["border"])
        pdf.roundRect(margin, y - block_h, content_width, block_h, 8, fill=1, stroke=1)

        pdf.setFillColor(palette["brand_dark"])
        pdf.setFont("Helvetica-Bold", 11)
        pdf.drawString(margin + 10, y - 16, title)

        pdf.setFillColor(palette["text"])
        pdf.setFont("Helvetica", 9)
        line_y = y - 32
        for line in wrapped:
            pdf.drawString(margin + 10, line_y, line)
            line_y -= 12

        y -= block_h + 12

    draw_header()
    draw_score_cards()
    if payload.get("overall_verdict"):
        draw_paragraph_block("Overall Verdict", str(payload.get("overall_verdict")))
    draw_paragraph_block("Target Profile", str(payload.get("target_profile", "N/A")))
    draw_paragraph_block("Narrative Feedback", str(payload.get("narrative_feedback", "")))

    draw_section("Strengths", payload.get("strengths") or [], tone="success")
    draw_section("Critical Risks", payload.get("risks") or [], tone="danger")
    draw_section("Quick Wins", payload.get("quick_wins") or [], tone="default")
    draw_section("Missing Skills", payload.get("missing_skills") or [], tone="default")
    draw_section("Must Fix Now", payload.get("must_fix_now") or [], tone="danger")
    draw_section("Improve Next", payload.get("improve_next") or [], tone="default")
    draw_section("Polish Later", payload.get("polish_later") or [], tone="success")

    if payload.get("missing_jd_keywords"):
        draw_section("Missing JD Keywords", payload.get("missing_jd_keywords") or [], tone="default")

    draw_section("Improvement Suggestions", payload.get("suggestions") or [], tone="default")

    rewrites = payload.get("rewrite_guidance") or []
    if rewrites:
        formatted_rewrites = [str(item).replace("\n", " | ") for item in rewrites[:6]]
        draw_section("Fact-Preserving Rewrite Guidance", formatted_rewrites, tone="default")

    ensure_space(20)
    pdf.setStrokeColor(palette["border"])
    pdf.line(margin, margin + 8, margin + content_width, margin + 8)
    pdf.setFont("Helvetica", 8)
    pdf.setFillColor(palette["muted"])
    pdf.drawString(margin, margin - 4, "Generated by Reskill Resume Analyzer")
    pdf.drawRightString(margin + content_width, margin - 4, f"Processing time: {payload.get('elapsed_ms', 0)} ms")

    pdf.save()
    return buffer.getvalue()


def _infer_default_role_from_title(title: str) -> str:
    normalized = title.lower().strip()
    if any(token in normalized for token in ["backend", "api", "server", "platform"]):
        return "backend_developer"
    if any(token in normalized for token in ["frontend", "react", "ui", "web"]):
        return "frontend_developer"
    if any(token in normalized for token in ["data", "ml", "ai", "analytics"]):
        return "data_scientist"
    return "default"


def _inject_theme_css() -> None:
        st.markdown(
                """
<style>
    /* -- Reset Streamlit defaults -- */
    #MainMenu, footer, header { visibility: hidden; }
    .block-container { padding: 1.5rem 2rem !important; max-width: 100% !important; }
    .stApp { background: #0D1117 !important; }

    /* -- Typography -- */
    html, body, [class*="css"] {
        font-family: 'Segoe UI', system-ui, -apple-system, sans-serif !important;
        color: #C9D1D9;
    }
    h1 { font-size: 22px !important; font-weight: 800 !important; color: #58A6FF !important; letter-spacing: 0.3px; }
    h2 { font-size: 16px !important; font-weight: 700 !important; color: #E6EDF3 !important; }
    h3 { font-size: 13px !important; font-weight: 600 !important; color: #C9D1D9 !important; }
    p, label, span, div { color: #C9D1D9; }

    /* -- Topbar / App header area -- */
    .app-topbar {
        background: #161B22;
        border: 1px solid #21262D;
        border-radius: 10px;
        padding: 14px 20px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 20px;
    }

    /* -- Section labels -- */
    .section-label {
        font-size: 10px !important;
        font-weight: 700 !important;
        letter-spacing: 1.2px !important;
        color: #7D8590 !important;
        text-transform: uppercase !important;
        margin-bottom: 14px !important;
    }

    /* -- Cards -- */
    .reskill-card {
        background: #161B22;
        border: 1px solid #21262D;
        border-radius: 10px;
        padding: 16px;
        margin-bottom: 12px;
    }

    /* -- Metric cards (score boxes) -- */
    [data-testid="metric-container"] {
        background: #161B22 !important;
        border: 1px solid #21262D !important;
        border-radius: 10px !important;
        padding: 14px !important;
    }
    [data-testid="metric-container"] label {
        font-size: 10px !important;
        font-weight: 700 !important;
        letter-spacing: 1px !important;
        color: #7D8590 !important;
        text-transform: uppercase !important;
    }
    [data-testid="stMetricValue"] {
        font-size: 28px !important;
        font-weight: 800 !important;
        color: #E6EDF3 !important;
    }
    [data-testid="stMetricDelta"] { font-size: 11px !important; }

    /* -- Text inputs -- */
    .stTextInput input, .stTextArea textarea {
        background: #161B22 !important;
        border: 1px solid #30363D !important;
        border-radius: 8px !important;
        color: #C9D1D9 !important;
        font-size: 13px !important;
        padding: 9px 13px !important;
    }
    .stTextInput input:focus, .stTextArea textarea:focus {
        border-color: #58A6FF !important;
        box-shadow: 0 0 0 3px rgba(88,166,255,0.12) !important;
    }
    .stTextInput input::placeholder, .stTextArea textarea::placeholder { color: #484F58 !important; }

    /* -- Select boxes -- */
    .stSelectbox [data-baseweb="select"] > div {
        background: #161B22 !important;
        border: 1px solid #30363D !important;
        border-radius: 8px !important;
        color: #C9D1D9 !important;
        font-size: 13px !important;
    }
    .stSelectbox [data-baseweb="select"] > div:hover { border-color: #58A6FF !important; }

    /* -- File uploader -- */
    [data-testid="stFileUploadDropzone"] {
        background: #161B22 !important;
        border: 2px dashed #30363D !important;
        border-radius: 10px !important;
        transition: border-color 0.2s !important;
    }
    [data-testid="stFileUploadDropzone"]:hover {
        border-color: #58A6FF !important;
        background: #0D1F3A !important;
    }
    [data-testid="stFileUploadDropzone"] p,
    [data-testid="stFileUploadDropzone"] span { color: #7D8590 !important; font-size: 12px !important; }

    /* -- Analyze button -- */
    .stButton > button[kind="primary"], .stButton > button {
        background: linear-gradient(90deg, #1F6FEB, #17A86A) !important;
        border: none !important;
        border-radius: 10px !important;
        color: white !important;
        font-size: 14px !important;
        font-weight: 700 !important;
        padding: 12px 24px !important;
        width: 100% !important;
        letter-spacing: 0.3px !important;
        transition: opacity 0.2s !important;
    }
    .stButton > button:hover { opacity: 0.88 !important; }
    .stButton > button:active { transform: scale(0.99) !important; }

    /* -- Download button -- */
    .stDownloadButton > button {
        background: #0D2A1A !important;
        border: 1px solid #3FB950 !important;
        color: #3FB950 !important;
        border-radius: 8px !important;
        font-size: 12px !important;
        font-weight: 600 !important;
    }

    /* -- Expanders -- */
    .streamlit-expanderHeader {
        background: #161B22 !important;
        border: 1px solid #21262D !important;
        border-radius: 8px !important;
        color: #C9D1D9 !important;
        font-size: 13px !important;
        font-weight: 600 !important;
    }
    .streamlit-expanderContent {
        background: #0D1117 !important;
        border: 1px solid #21262D !important;
        border-top: none !important;
        border-radius: 0 0 8px 8px !important;
        padding: 14px !important;
    }

    /* -- Tabs -- */
    .stTabs [data-baseweb="tab-list"] {
        background: #161B22 !important;
        border-radius: 10px !important;
        padding: 4px !important;
        gap: 2px !important;
        border: 1px solid #21262D !important;
    }
    .stTabs [data-baseweb="tab"] {
        background: transparent !important;
        color: #7D8590 !important;
        border-radius: 7px !important;
        padding: 6px 16px !important;
        font-size: 12px !important;
        font-weight: 500 !important;
        border: none !important;
    }
    .stTabs [aria-selected="true"] {
        background: #21262D !important;
        color: #E6EDF3 !important;
        font-weight: 700 !important;
    }

    /* -- Progress bars -- */
    .stProgress > div > div > div {
        background: linear-gradient(90deg, #F85149, #E3B341 50%, #3FB950) !important;
        border-radius: 4px !important;
    }
    .stProgress > div > div { background: #21262D !important; border-radius: 4px !important; }

    /* -- Dividers -- */
    hr { border-color: #21262D !important; }

    /* -- Sidebar (if used) -- */
    [data-testid="stSidebar"] {
        background: #0D1117 !important;
        border-right: 1px solid #21262D !important;
    }
    [data-testid="stSidebar"] * { color: #C9D1D9 !important; }

    /* -- Spinner -- */
    .stSpinner > div { border-top-color: #58A6FF !important; }

    /* -- Alerts / Info boxes -- */
    .stAlert { border-radius: 8px !important; border: none !important; }
    [data-baseweb="notification"] { background: #0C2D4F !important; border: 1px solid #1F6FEB !important; border-radius: 8px !important; }

    /* -- Privacy bar component -- */
    .privacy-bar {
        background: #161B22;
        border: 1px solid #21262D;
        border-radius: 8px;
        padding: 10px 16px;
        font-size: 11px;
        color: #7D8590;
        margin-bottom: 16px;
        display: flex;
        align-items: center;
        gap: 8px;
    }

    /* -- Score metric cards row -- */
    .score-grid {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 10px;
        margin-bottom: 20px;
    }
    .score-card {
        background: #161B22;
        border: 1px solid #21262D;
        border-radius: 10px;
        padding: 14px;
        text-align: center;
    }
    .score-card-label {
        font-size: 9px;
        font-weight: 700;
        letter-spacing: 1px;
        color: #7D8590;
        text-transform: uppercase;
        margin-bottom: 6px;
    }
    .score-card-value {
        font-size: 26px;
        font-weight: 800;
        color: #E6EDF3;
    }
    .score-card-value.pending { color: #30363D; }

    /* -- Keyword pills -- */
    .kw-missing {
        display: inline-block;
        background: #1A0E0E;
        color: #F85149;
        border: 1px solid #3D1515;
        border-radius: 12px;
        padding: 3px 10px;
        font-size: 11px;
        margin: 3px;
        font-weight: 500;
    }
    .kw-matched {
        display: inline-block;
        background: #0D1F14;
        color: #3FB950;
        border: 1px solid #1A3A24;
        border-radius: 12px;
        padding: 3px 10px;
        font-size: 11px;
        margin: 3px;
        font-weight: 500;
    }
    .kw-partial {
        display: inline-block;
        background: #3D2F00;
        color: #E3B341;
        border: 1px solid #6B4F00;
        border-radius: 12px;
        padding: 3px 10px;
        font-size: 11px;
        margin: 3px;
        font-weight: 500;
    }

    /* -- Issue cards (weaker vs stronger) -- */
    .compare-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 10px;
        margin-top: 10px;
    }
    .weaker-box {
        background: #1A0E0E;
        border: 1px solid #3D1515;
        border-radius: 8px;
        padding: 12px;
    }
    .stronger-box {
        background: #0D1F14;
        border: 1px solid #1A3A24;
        border-radius: 8px;
        padding: 12px;
    }
    .box-tag-weak { font-size: 9px; font-weight: 700; color: #F85149; letter-spacing: 1px; margin-bottom: 6px; }
    .box-tag-strong { font-size: 9px; font-weight: 700; color: #3FB950; letter-spacing: 1px; margin-bottom: 6px; }

    /* -- ATS bar rows -- */
    .ats-row {
        display: flex;
        align-items: center;
        gap: 10px;
        margin-bottom: 8px;
    }
    .ats-bar-label { font-size: 11px; color: #7D8590; width: 130px; flex-shrink: 0; }
    .ats-bar-track { flex: 1; height: 6px; background: #21262D; border-radius: 3px; overflow: hidden; }
    .ats-bar-fill-green { height: 100%; background: #3FB950; border-radius: 3px; }
    .ats-bar-fill-yellow { height: 100%; background: #E3B341; border-radius: 3px; }
    .ats-bar-fill-red { height: 100%; background: #F85149; border-radius: 3px; }
    .ats-bar-val { font-size: 11px; color: #C9D1D9; font-weight: 600; width: 32px; text-align: right; }
</style>
""",
                unsafe_allow_html=True,
        )


def render_score_cards(ats_score: int | None, jd_match: int | None, impact_score: int | None, overall_score: int | None) -> None:
        def score_color(value: int | None) -> str:
                if value is None:
                        return "#30363D"
                if value >= 70:
                        return "#3FB950"
                if value >= 40:
                        return "#E3B341"
                return "#F85149"

        def fmt(value: int | None) -> str:
                return str(value) if value is not None else "--"

        st.markdown(
                f"""
        <div class="score-grid">
            <div class="score-card">
                <div class="score-card-label">ATS Score</div>
                <div class="score-card-value" style="color:{score_color(ats_score)};">{fmt(ats_score)}</div>
            </div>
            <div class="score-card">
                <div class="score-card-label">JD Match</div>
                <div class="score-card-value" style="color:{score_color(jd_match)};">{fmt(jd_match)}%</div>
            </div>
            <div class="score-card">
                <div class="score-card-label">Impact</div>
                <div class="score-card-value" style="color:{score_color(impact_score)};">{fmt(impact_score)}</div>
            </div>
            <div class="score-card">
                <div class="score-card-label">Overall</div>
                <div class="score-card-value" style="color:{score_color(overall_score)};">{fmt(overall_score)}</div>
            </div>
        </div>
        """,
                unsafe_allow_html=True,
        )


def render_keywords(matched: list[str], missing: list[str], partial: list[str] | None = None) -> None:
        pills = ""
        for keyword in matched:
                pills += f'<span class="kw-matched">{keyword}</span>'
        for keyword in partial or []:
                pills += f'<span class="kw-partial">{keyword}</span>'
        for keyword in missing:
                pills += f'<span class="kw-missing">{keyword}</span>'
        st.markdown(f'<div style="line-height:2.2;">{pills}</div>', unsafe_allow_html=True)


def render_ats_bars(scores: dict[str, int]) -> None:
        html = ""
        for label, val in scores.items():
                if val >= 70:
                        fill_class = "ats-bar-fill-green"
                elif val >= 40:
                        fill_class = "ats-bar-fill-yellow"
                else:
                        fill_class = "ats-bar-fill-red"
                html += (
                        "<div class=\"ats-row\">"
                        + f"<span class=\"ats-bar-label\">{label}</span>"
                        + f"<div class=\"ats-bar-track\"><div class=\"{fill_class}\" style=\"width:{val}%;\"></div></div>"
                        + f"<span class=\"ats-bar-val\">{val}%</span>"
                        + "</div>"
                )
        st.markdown(html, unsafe_allow_html=True)


def render_comparison_card(title: str, issue_num: int, description: str, weak: str, strong: str) -> None:
        st.markdown(
                f"""
        <div class="reskill-card">
            <div style="display:flex;align-items:center;gap:10px;margin-bottom:10px;">
                <div style="width:26px;height:26px;border-radius:50%;background:#0C2D4F;color:#58A6FF;
                                        font-size:12px;font-weight:700;display:flex;align-items:center;justify-content:center;flex-shrink:0;">
                    {issue_num}
                </div>
                <span style="font-size:14px;font-weight:700;color:#E6EDF3;">{title}</span>
            </div>
            <p style="font-size:12px;color:#7D8590;margin-bottom:12px;">{description}</p>
            <div class="compare-grid">
                <div class="weaker-box">
                    <div class="box-tag-weak">WEAKER</div>
                    <div style="font-size:11px;color:#7D8590;line-height:1.6;">{weak}</div>
                </div>
                <div class="stronger-box">
                    <div class="box-tag-strong">STRONGER</div>
                    <div style="font-size:11px;color:#C9D1D9;line-height:1.6;">{strong}</div>
                </div>
            </div>
        </div>
        """,
                unsafe_allow_html=True,
        )


def render_empty_state() -> None:
        st.markdown(
                """
        <div style="display:flex;flex-direction:column;align-items:center;justify-content:center;
                                padding:60px 20px;text-align:center;">
            <div style="width:72px;height:72px;border-radius:50%;border:2px dashed #30363D;
                                    display:flex;align-items:center;justify-content:center;margin-bottom:16px;">
                <svg width="28" height="28" viewBox="0 0 28 28" fill="none">
                    <circle cx="14" cy="14" r="10" stroke="#30363D" stroke-width="2"/>
                    <path d="M14 9v5l3 3" stroke="#58A6FF" stroke-width="1.5" stroke-linecap="round"/>
                </svg>
            </div>
            <div style="font-size:15px;font-weight:700;color:#C9D1D9;margin-bottom:8px;">Ready to analyze</div>
            <div style="font-size:12px;color:#7D8590;max-width:220px;line-height:1.6;">
                Fill in your target role, upload your resume, then click Analyze Resume
            </div>
        </div>
        """,
                unsafe_allow_html=True,
        )


def main() -> None:
    st.set_page_config(
        page_title="Reskill - AI based Resume Analyzer",
        page_icon=":page_facing_up:",
        layout="wide",
        initial_sidebar_state="collapsed",
    )

    _inject_theme_css()

    if "resume_text" not in st.session_state:
        st.session_state.resume_text = ""
    if "analysis_done" not in st.session_state:
        st.session_state.analysis_done = False
    if "analysis_result" not in st.session_state:
        st.session_state.analysis_result = None

    st.markdown(
        """
<div class="app-topbar">
  <div>
    <div style="font-size:18px;font-weight:800;color:#58A6FF;letter-spacing:0.3px;">
      RESKILL
      <span style="color:#7D8590;font-weight:400;font-size:12px;margin-left:10px;">
        AI Resume Analyzer
      </span>
    </div>
    <div style="font-size:11px;color:#7D8590;margin-top:2px;">
      Standalone resume analysis · ATS scoring · Role match
    </div>
  </div>
  <div style="display:flex;gap:8px;">
    <span style="background:#0C2D4F;color:#58A6FF;font-size:10px;padding:3px 10px;border-radius:10px;font-weight:600;">v2.0</span>
    <span style="background:#0D2A1A;color:#3FB950;font-size:10px;padding:3px 10px;border-radius:10px;font-weight:600;">Live</span>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )

    st.markdown(
        """
<div class="privacy-bar">
  <div style="width:18px;height:18px;background:#0C2D4F;border-radius:4px;display:flex;align-items:center;justify-content:center;flex-shrink:0;">
    <span style="color:#58A6FF;font-size:9px;font-weight:800;">S</span>
  </div>
  <span>Your resume data is processed locally and never stored on our servers.</span>
</div>
""",
        unsafe_allow_html=True,
    )
    with st.expander("Privacy & Reliability details"):
        st.markdown("All analysis is performed in-session. No data is retained after you close the app.")

    col_input, col_results = st.columns([1, 1], gap="large")

    with col_input:
        st.markdown('<div class="section-label">Resume + Target Role Input</div>', unsafe_allow_html=True)

        target_title = st.text_input(
            "Target Job Title",
            value="",
            placeholder="Example: Senior Backend Engineer",
            help="Type the exact role you are targeting.",
        )

        c_role_1, c_role_2 = st.columns(2)
        with c_role_1:
            seniority = st.selectbox(
                "Seniority",
                options=SENIORITY_OPTIONS,
                index=2,
                help="Used to tailor recommendations and leadership depth.",
            )
        with c_role_2:
            industry = st.text_input(
                "Industry",
                value="",
                placeholder="Example: Fintech, Healthcare, SaaS",
            )

        inferred_role = _infer_default_role_from_title(target_title)
        selected_role = st.selectbox(
            "Role Mapping (auto-inferred, editable)",
            options=list(ROLE_OPTIONS.keys()),
            index=list(ROLE_OPTIONS.keys()).index(inferred_role),
            format_func=lambda key: ROLE_OPTIONS[key],
            help="Auto-selected from target title. Adjust manually if needed.",
        )

        uploaded_file = st.file_uploader(
            "Upload Resume",
            type=["txt", "pdf", "docx"],
            help="Supported formats: TXT, PDF, DOCX",
        )

        jd_text = st.text_area(
            "Job Description (optional, for JD matching)",
            value="",
            height=180,
            max_chars=30000,
            placeholder="Paste the job description to get JD match score and missing JD keywords.",
        )

        if uploaded_file is not None:
            if getattr(uploaded_file, "size", 0) > 10 * 1024 * 1024:
                st.error("Uploaded file is too large. Max allowed is 10 MB.")
                uploaded_file = None

        if uploaded_file is not None:
            extracted = _extract_text_from_uploaded_file(uploaded_file)
            if extracted:
                st.session_state.resume_text = extracted
                st.success(f"Loaded text from {uploaded_file.name}")
            else:
                st.error("Could not extract text from the uploaded file.")

        resume_text = st.text_area(
            "Resume Text",
            value=st.session_state.resume_text,
            height=320,
            max_chars=12000,
            placeholder="Paste resume content here, or upload a file above.",
            key="resume_text_area",
        )
        st.session_state.resume_text = resume_text

        analyze_clicked = st.button("Analyze Resume", type="primary", use_container_width=True)

        if analyze_clicked:
            if not target_title.strip():
                st.error("Please enter a target job title.")
            elif not resume_text.strip():
                st.error("Please upload a resume or paste resume text before analyzing.")
            elif len(resume_text.strip()) < 30:
                st.error("Resume content is too short. Please provide at least 30 characters.")
            else:
                with st.spinner("🔍 Reskill is analyzing your resume..."):
                    result = analyze_resume(
                        ResumeInput(
                            role=selected_role,
                            resume_text=resume_text,
                            target_title=target_title,
                            seniority=seniority,
                            industry=industry,
                            job_description=jd_text,
                        )
                    )
                    st.session_state.analysis_result = result
                    st.session_state["analysis_done"] = True

    with col_results:
        st.markdown('<div class="section-label">Analysis Results</div>', unsafe_allow_html=True)

        if not st.session_state.get("analysis_done", False) or st.session_state.analysis_result is None:
            render_empty_state()
            return

        result = st.session_state.analysis_result
        if result.error:
            st.warning(result.error)
            return

        impact_score = result.section_scores.get("impact", 0)
        render_score_cards(result.ats_score, result.jd_match_score, impact_score, result.score)

        st.markdown(f"### Verdict: {_score_badge(result.score)}")
        st.caption(f"{result.overall_verdict} | Confidence: {str(result.confidence_level).upper()}")
        st.write(result.narrative_feedback)

        ats_rows = {
            "Keyword Match": int(result.keyword_coverage or 0),
            "Formatting": int(result.section_scores.get("clarity", 0)),
            "Section Headers": int(result.section_scores.get("ats_compatibility", 0)),
            "Readability": int(result.section_scores.get("relevance", 0)),
        }
        st.markdown("### ATS Breakdown")
        render_ats_bars(ats_rows)

        required_skills = ROLE_SKILLS.get(result.role_used, [])
        matched_skills = [skill for skill in required_skills if skill not in result.missing_skills]
        partial_keywords = list(result.missing_jd_keywords[:4]) if result.missing_jd_keywords else []
        st.markdown("### Role Keyword Signals")
        render_keywords(matched_skills, result.missing_skills, partial_keywords)

        st.markdown("### Resume Improvements")
        rewrites = list(result.rewrite_guidance or [])
        base_suggestions = list(result.suggestions or [])

        for idx, suggestion in enumerate(base_suggestions[:6], start=1):
            weak_text = "Generic resume statement without impact or role relevance."
            strong_text = "Action-driven bullet with clear scope, tools, and quantified outcome."
            if rewrites:
                rewrite = rewrites[(idx - 1) % len(rewrites)]
                if "Before:" in rewrite and "After:" in rewrite:
                    weak_text = rewrite.split("After:", 1)[0].replace("Before:", "").strip()
                    strong_text = rewrite.split("After:", 1)[1].strip()
            render_comparison_card(
                title=f"Improvement Opportunity {idx}",
                issue_num=idx,
                description=suggestion,
                weak=weak_text,
                strong=strong_text,
            )

        payload = {
            "score": result.score,
            "ats_score": result.ats_score,
            "keyword_coverage": result.keyword_coverage,
            "section_scores": result.section_scores,
            "jd_match_score": result.jd_match_score,
            "missing_jd_keywords": result.missing_jd_keywords,
            "rewrite_guidance": result.rewrite_guidance,
            "strengths": result.strengths,
            "risks": result.risks,
            "quick_wins": result.quick_wins,
            "narrative_feedback": result.narrative_feedback,
            "confidence_level": result.confidence_level,
            "overall_verdict": result.overall_verdict,
            "missing_skills": result.missing_skills,
            "suggestions": result.suggestions,
            "must_fix_now": result.must_fix_now,
            "improve_next": result.improve_next,
            "polish_later": result.polish_later,
            "role_used": result.role_used,
            "target_profile": result.target_profile,
            "truncated": result.truncated,
            "error": result.error,
            "elapsed_ms": result.elapsed_ms,
        }
        pdf_bytes = _build_pdf_report(payload)
        st.download_button(
            "Download PDF Report",
            data=pdf_bytes,
            file_name="resume_analysis_report.pdf",
            mime="application/pdf",
            use_container_width=True,
        )


if __name__ == "__main__":
    main()
