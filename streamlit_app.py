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


def _inject_theme_css(mode: str) -> None:
    if mode == "Night Shift":
        background = "radial-gradient(circle at 8% 0%, #14213f 0%, #0a142b 48%, #071022 100%)"
        panel_bg = "rgba(14, 27, 52, 0.92)"
        panel_border = "#2b4678"
        text_color = "#eff5ff"
        muted = "#aabfe0"
        title = "#8fc1ff"
        accent = "#3d93ff"
        accent_2 = "#1dc9a7"
        input_bg = "#132745"
        chip_bg = "#17345d"
    else:
        background = "radial-gradient(circle at 6% 0%, #f8fcff 0%, #edf4ff 54%, #e7eef8 100%)"
        panel_bg = "rgba(255, 255, 255, 0.95)"
        panel_border = "#ccd9ef"
        text_color = "#11233f"
        muted = "#4e6994"
        title = "#184b9e"
        accent = "#2a76e8"
        accent_2 = "#17b694"
        input_bg = "#f9fbff"
        chip_bg = "#eaf2ff"

    st.markdown(
        f"""
        <style>
        #MainMenu {{visibility: hidden;}}
        header {{visibility: hidden;}}
        footer {{visibility: hidden;}}
        [data-testid="stToolbar"] {{display: none !important;}}
        [data-testid="stDecoration"] {{display: none !important;}}
        [data-testid="stStatusWidget"] {{display: none !important;}}
        [data-testid="stDeployButton"] {{display: none !important;}}
        [data-testid="stNotification"] {{display: none !important;}}
        [data-testid="stSidebar"] {{display: none !important;}}
        [data-testid="stAppViewContainer"] {{
            background: {background};
        }}
        [data-testid="stHeader"] {{
            background: transparent;
            height: 0;
        }}
        .block-container {{
            max-width: 1480px;
            padding-top: 0.75rem;
            padding-bottom: 1.6rem;
        }}
        @keyframes fadeSlideIn {{
            from {{ opacity: 0; transform: translateY(8px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}
        @keyframes softPulse {{
            0% {{ box-shadow: 0 0 0 0 rgba(77,163,255,0.35); }}
            70% {{ box-shadow: 0 0 0 10px rgba(77,163,255,0); }}
            100% {{ box-shadow: 0 0 0 0 rgba(77,163,255,0); }}
        }}
        h1, h2, h3, p, label, span, li, div {{
            color: {text_color};
        }}
        div, p, label {{
            font-size: 1rem;
        }}
        .app-title {{
            color: {title};
            font-size: 2.15rem;
            font-weight: 800;
            letter-spacing: 0.15px;
            margin-bottom: 0.2rem;
            animation: fadeSlideIn 0.45s ease-out;
        }}
        .app-subtitle {{
            color: {muted};
            margin-bottom: 0.5rem;
            font-size: 1rem;
            animation: fadeSlideIn 0.7s ease-out;
        }}
        .top-note {{
            color: {muted};
            font-size: 0.9rem;
            margin-bottom: 0.7rem;
        }}
        .panel {{
            border: 1px solid {panel_border};
            border-radius: 18px;
            padding: 1rem 1.1rem;
            background: {panel_bg};
            box-shadow: 0 14px 34px rgba(10, 24, 48, 0.12);
            backdrop-filter: blur(6px);
            animation: fadeSlideIn 0.5s ease-out;
        }}
        .hero-strip {{
            border-radius: 14px;
            padding: 0.65rem 0.85rem;
            border: 1px solid {panel_border};
            background: linear-gradient(130deg, {chip_bg}, {panel_bg});
            margin-bottom: 0.65rem;
            color: {text_color};
            font-size: 0.92rem;
        }}
        .label-chip {{
            display: inline-block;
            border: 1px solid {panel_border};
            background: {chip_bg};
            color: {muted};
            border-radius: 999px;
            padding: 0.2rem 0.6rem;
            font-size: 0.76rem;
            margin-right: 0.35rem;
            margin-bottom: 0.35rem;
        }}
        .priority-block {{
            border: 1px solid {panel_border};
            border-left: 4px solid {accent};
            border-radius: 12px;
            padding: 0.6rem 0.75rem;
            margin-bottom: 0.55rem;
            background: {chip_bg};
        }}
        .priority-title {{
            color: {title};
            font-size: 0.85rem;
            font-weight: 700;
            margin-bottom: 0.35rem;
            text-transform: uppercase;
            letter-spacing: 0.3px;
        }}
        .priority-block ul {{
            margin: 0.1rem 0 0.1rem 1rem;
            padding-left: 0.2rem;
        }}
        .priority-block li {{
            margin-bottom: 0.25rem;
            color: {text_color};
        }}
        [data-testid="stMetric"] {{
            background: {panel_bg};
            border: 1px solid {panel_border};
            border-radius: 14px;
            padding: 0.7rem;
            animation: fadeSlideIn 0.55s ease-out;
        }}
        [data-baseweb="input"] input,
        [data-baseweb="textarea"] textarea,
        [data-baseweb="select"] > div,
        textarea {{
            background: {input_bg} !important;
            border-radius: 10px !important;
        }}
        [data-testid="stButton"] button,
        [data-testid="stDownloadButton"] button {{
            border-radius: 12px !important;
            border: 1px solid {accent} !important;
            background: linear-gradient(120deg, {accent}, {accent_2}) !important;
            color: white !important;
            font-weight: 700 !important;
            letter-spacing: 0.2px;
            min-height: 2.6rem;
            transition: all 0.2s ease !important;
        }}
        [data-testid="stButton"] button:hover,
        [data-testid="stDownloadButton"] button:hover {{
            filter: brightness(1.06);
            transform: translateY(-1px);
        }}
        [role="radiogroup"] {{
            display: flex;
            justify-content: flex-end;
            gap: 0.4rem;
        }}
        [role="radiogroup"] > label {{
            border: 1px solid {panel_border};
            border-radius: 999px;
            padding: 0.25rem 0.6rem;
            background: {chip_bg};
            color: {text_color};
            font-weight: 600;
        }}
        </style>
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

    if "theme_mode" not in st.session_state:
        st.session_state.theme_mode = "Daylight"
    if "store_history" not in st.session_state:
        st.session_state.store_history = False
    if "analysis_history" not in st.session_state:
        st.session_state.analysis_history = []
    if "live_feedback" not in st.session_state:
        st.session_state.live_feedback = True
    if "last_score" not in st.session_state:
        st.session_state.last_score = None

    top_left, top_right = st.columns([3, 1])
    with top_left:
        st.markdown("<div class='app-title'>Reskill - AI based Resume Analyzer</div>", unsafe_allow_html=True)
        st.markdown("<div class='app-subtitle'>Standalone resume analysis with role match and ATS scoring</div>", unsafe_allow_html=True)
        st.markdown(
            "<div class='top-note'>Upload your resume, align to a target role, then get prioritized fixes you can apply immediately.</div>",
            unsafe_allow_html=True,
        )
    with top_right:
        selected_theme = st.radio(
            "Theme",
            options=["Daylight", "Night Shift"],
            index=0 if st.session_state.theme_mode == "Daylight" else 1,
            horizontal=True,
            label_visibility="collapsed",
        )
        st.session_state.theme_mode = selected_theme

    _inject_theme_css(st.session_state.theme_mode)

    with st.expander("Privacy & Reliability", expanded=False):
        st.caption("Session-only by default: resume/JD data is processed in-memory and not persisted to disk.")
        st.session_state.store_history = st.checkbox(
            "Keep analysis history in this browser session only",
            value=st.session_state.store_history,
        )
        st.session_state.live_feedback = st.checkbox(
            "Enable live feedback while editing",
            value=st.session_state.live_feedback,
        )
        if st.button("Clear session data", use_container_width=True):
            for key in ["resume_text", "analysis_history", "resume_text_area", "last_score"]:
                if key in st.session_state:
                    del st.session_state[key]
            st.success("Session data cleared.")

    left, right = st.columns([1, 1])

    with left:
        st.markdown("<div class='panel'>", unsafe_allow_html=True)
        st.subheader("Resume + Target Role Input")

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

        if "resume_text" not in st.session_state:
            st.session_state.resume_text = ""

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
        st.markdown("</div>", unsafe_allow_html=True)

    with right:
        st.markdown("<div class='panel'>", unsafe_allow_html=True)
        st.subheader("Analysis Results")
        result = None
        is_live_preview = False

        if not target_title.strip() and analyze_clicked:
            st.error("Please enter a target job title.")
        elif not resume_text.strip() and analyze_clicked:
            st.error("Please upload a resume or paste resume text before analyzing.")
        elif len(resume_text.strip()) < 30 and analyze_clicked:
            st.error("Resume content is too short. Please provide at least 30 characters.")
        else:
            should_run_live = (
                st.session_state.live_feedback
                and not analyze_clicked
                and target_title.strip()
                and len(resume_text.strip()) >= 30
            )
            if analyze_clicked or should_run_live:
                is_live_preview = should_run_live
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

        if result is not None:
            if is_live_preview:
                st.info("Live feedback preview: updates as you edit resume and role inputs.")

            if result.error:
                st.warning(result.error)
            else:
                score_delta = None
                if st.session_state.last_score is not None:
                    score_delta = result.score - st.session_state.last_score
                st.session_state.last_score = result.score

                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Role Match Score", f"{result.score}/100", delta=score_delta)
                c2.metric("ATS Score", f"{result.ats_score}/100")
                c3.metric("Keyword Coverage", f"{result.keyword_coverage or 0}%")
                c4.metric("Role Used", ROLE_OPTIONS.get(result.role_used, result.role_used))

                st.markdown(
                    "<div class='hero-strip'><strong>Verdict:</strong> "
                    + str(result.overall_verdict)
                    + "</div>",
                    unsafe_allow_html=True,
                )

                st.markdown(
                    "<span class='label-chip'>Target: "
                    + str(result.target_profile)
                    + "</span>"
                    + "<span class='label-chip'>Confidence: "
                    + str(result.confidence_level).upper()
                    + "</span>",
                    unsafe_allow_html=True,
                )

                if result.jd_match_score is not None:
                    st.metric("JD Match Score", f"{result.jd_match_score}/100")

                if result.confidence_level == "high":
                    st.success("Feedback confidence: HIGH")
                elif result.confidence_level == "medium":
                    st.warning("Feedback confidence: MEDIUM")
                else:
                    st.error("Feedback confidence: LOW")

                st.caption(f"Target Profile: {result.target_profile}")
                st.write(result.narrative_feedback)

                st.caption(
                    f"Role grade: {_score_badge(result.score)} | "
                    f"ATS grade: {_score_badge(result.ats_score)} | "
                    f"Processed in {result.elapsed_ms} ms"
                )

                st.progress((result.score or 0) / 100.0, text="Role Match")
                st.progress((result.ats_score or 0) / 100.0, text="ATS Compatibility")
                st.progress((result.keyword_coverage or 0) / 100.0, text="Role Keyword Coverage")
                if result.jd_match_score is not None:
                    st.progress((result.jd_match_score or 0) / 100.0, text="Job Description Match")

                st.markdown("### Strengths")
                for item in result.strengths:
                    st.write(f"- {item}")

                st.markdown("### Critical Risks")
                for item in result.risks:
                    st.write(f"- {item}")

                st.markdown("### Quick Wins (Next 30 Minutes)")
                for item in result.quick_wins:
                    st.write(f"- {item}")

                if result.must_fix_now or result.improve_next or result.polish_later:
                    st.markdown("### Priority Action Plan")
                    if result.must_fix_now:
                        bullets = "".join([f"<li>{item}</li>" for item in result.must_fix_now])
                        st.markdown(
                            "<div class='priority-block'><div class='priority-title'>Must Fix Now</div><ul>"
                            + bullets
                            + "</ul></div>",
                            unsafe_allow_html=True,
                        )

                    if result.improve_next:
                        bullets = "".join([f"<li>{item}</li>" for item in result.improve_next])
                        st.markdown(
                            "<div class='priority-block'><div class='priority-title'>Improve Next</div><ul>"
                            + bullets
                            + "</ul></div>",
                            unsafe_allow_html=True,
                        )

                    if result.polish_later:
                        bullets = "".join([f"<li>{item}</li>" for item in result.polish_later])
                        st.markdown(
                            "<div class='priority-block'><div class='priority-title'>Polish Later</div><ul>"
                            + bullets
                            + "</ul></div>",
                            unsafe_allow_html=True,
                        )

                if result.missing_jd_keywords:
                    st.markdown("### Missing JD Keywords")
                    st.write(", ".join(result.missing_jd_keywords))

                st.markdown("### Resume Section Scores")
                for name, value in result.section_scores.items():
                    st.progress(value / 100.0, text=f"{name.title()}: {value}/100")

                st.markdown("### Missing Skills")
                if result.missing_skills:
                    for skill in result.missing_skills:
                        st.write(f"- {skill}")
                else:
                    st.success("No required skills missing for this role.")

                st.markdown("### Improvement Suggestions")
                for idx, suggestion in enumerate(result.suggestions, start=1):
                    st.write(f"{idx}. {suggestion}")

                st.markdown("### Fact-Preserving Rewrite Guidance")
                for idx, rewrite in enumerate(result.rewrite_guidance, start=1):
                    st.markdown(
                        "<div class='panel' style='margin-bottom:0.6rem;'>"
                        + f"<strong>Rewrite {idx}</strong><br>"
                        + rewrite.replace("\n", "<br>")
                        + "</div>",
                        unsafe_allow_html=True,
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

                if st.session_state.store_history and analyze_clicked:
                    st.session_state.analysis_history.append(payload)
                    st.info(f"Saved this result in session history ({len(st.session_state.analysis_history)} items).")
        else:
            st.info("Run an analysis to see scores, missing skills, and ATS feedback.")

        st.markdown("</div>", unsafe_allow_html=True)


if __name__ == "__main__":
    main()
