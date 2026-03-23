"""Main Streamlit entry point for Reskill. UI orchestration only; analysis logic lives in modules."""

from __future__ import annotations

from datetime import datetime

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from config import (
    DEFAULTS,
    LOG_FILE,
    MAX_JD_CHARS,
    MAX_RESUME_CHARS,
    MAX_UPLOAD_BYTES,
    ROLE_MAPPING_OPTIONS,
    SENIORITY_OPTIONS,
)
from modules.ai_rewriter import generate_summary, rewrite_bullet, suggest_improvements
from modules.ats_checker import check_ats
from modules.bullet_analyzer import analyze_bullets
from modules.jd_matcher import match_job_description
from modules.pdf_parser import ParseError, extract_contact_info, parse_resume_file
from modules.recommender import recommend_courses_and_jobs
from modules.report_generator import generate_pdf_report
from modules.resume_scorer import score_resume
from modules.section_detector import split_sections
from modules.skill_extractor import extract_skills


def _init_session() -> None:
    for key, val in DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = val
    if "analysis_running" not in st.session_state:
        st.session_state.analysis_running = False


def _infer_role(title: str) -> str:
    t = title.lower()
    if any(k in t for k in ["data", "ml", "ai"]):
        return "data_scientist"
    if any(k in t for k in ["product", "pm"]):
        return "product_manager"
    if any(k in t for k in ["devops", "platform", "sre"]):
        return "devops_engineer"
    if any(k in t for k in ["design", "ux", "ui"]):
        return "designer"
    if any(k in t for k in ["marketing", "growth"]):
        return "marketing"
    if any(k in t for k in ["engineer", "developer", "software"]):
        return "software_engineer"
    return "general_role"


def _theme_vars() -> dict:
    if st.session_state.dark_mode:
        return {
            "bg_main": "#0D1117",
            "bg_card": "#161B22",
            "bg_border": "#21262D",
            "text_primary": "#E6EDF3",
            "text_muted": "#7D8590",
        }
    return {
        "bg_main": "#F6F8FA",
        "bg_card": "#FFFFFF",
        "bg_border": "#D0D7DE",
        "text_primary": "#1F2328",
        "text_muted": "#656D76",
    }


def _inject_css(theme: dict) -> None:
    st.markdown(
        f"""
<style>
#MainMenu, footer, header {{ visibility: hidden; }}
.block-container {{ max-width: 1360px !important; padding: 1.2rem 1.4rem 2rem !important; }}
.stApp {{ background: {theme['bg_main']} !important; }}
html, body, [class*="css"] {{ color: {theme['text_primary']} !important; font-family: 'Segoe UI', sans-serif !important; }}

.topbar {{ display:flex; justify-content:space-between; align-items:center; margin-bottom: 12px; }}
.hero {{ background:{theme['bg_card']}; border:1px solid {theme['bg_border']}; border-radius:12px; padding:20px; margin-bottom:14px; }}
.hero-title {{ font-size:42px; font-weight:800; color:#58A6FF; letter-spacing:0.4px; }}
.hero-sub {{ font-size:15px; color:{theme['text_muted']}; margin-top:4px; }}
.badge-row {{ display:flex; gap:8px; margin-top:14px; flex-wrap:wrap; }}
.stat-badge {{ background:{theme['bg_main']}; border:1px solid {theme['bg_border']}; border-radius:999px; padding:6px 10px; font-size:12px; color:{theme['text_muted']}; }}

.privacy {{ background:{theme['bg_card']}; border:1px solid {theme['bg_border']}; border-radius:8px; padding:8px 12px; font-size:12px; margin-bottom:10px; color:{theme['text_muted']}; }}
.panel {{ background:{theme['bg_card']}; border:1px solid {theme['bg_border']}; border-radius:12px; padding:14px; }}
.section-label {{ font-size:10px; letter-spacing:1.1px; text-transform:uppercase; color:{theme['text_muted']}; font-weight:700; margin-bottom:10px; }}

[data-testid="stFileUploadDropzone"] {{ background:{theme['bg_card']} !important; border:2px dashed {theme['bg_border']} !important; border-radius:10px !important; }}
[data-testid="stFileUploadDropzone"]:hover {{ border-color:#58A6FF !important; }}
.stTextInput input, .stTextArea textarea {{ background:{theme['bg_card']} !important; border:1px solid {theme['bg_border']} !important; color:{theme['text_primary']} !important; }}
.stSelectbox [data-baseweb='select'] > div {{ background:{theme['bg_card']} !important; border:1px solid {theme['bg_border']} !important; color:{theme['text_primary']} !important; }}

.score-grid {{ display:grid; grid-template-columns: repeat(4, minmax(120px, 1fr)); gap:10px; margin-bottom:10px; }}
.score-card {{ background:{theme['bg_card']}; border:1px solid {theme['bg_border']}; border-radius:10px; padding:14px; text-align:center; }}
.score-label {{ font-size:10px; text-transform:uppercase; letter-spacing:1px; color:{theme['text_muted']}; font-weight:700; }}
.score-value {{ font-size:28px; font-weight:800; }}

.ats-row {{ display:flex; align-items:center; gap:10px; margin-bottom:8px; }}
.ats-label {{ width:130px; color:{theme['text_muted']}; font-size:12px; }}
.ats-track {{ flex:1; height:8px; border-radius:4px; background:{theme['bg_border']}; overflow:hidden; }}
.ats-val {{ width:36px; text-align:right; font-size:12px; font-weight:700; }}

.pill-wrap {{ line-height:2.2; }}
.kw {{ display:inline-block; margin:3px; padding:3px 10px; border-radius:12px; border:1px solid; font-size:11px; font-weight:500; }}
.kw.match {{ background:#0D1F14; color:#3FB950; border-color:#1A3A24; }}
.kw.miss {{ background:#1A0E0E; color:#F85149; border-color:#3D1515; }}
.kw.partial {{ background:#3D2F00; color:#E3B341; border-color:#6B4F00; }}

.compare-card {{ background:{theme['bg_card']}; border:1px solid {theme['bg_border']}; border-radius:10px; padding:14px; margin-bottom:10px; }}
.compare-grid {{ display:grid; grid-template-columns: 1fr 1fr; gap:10px; }}
.weak {{ background:#1A0E0E; border:1px solid #3D1515; border-radius:8px; padding:10px; font-size:12px; }}
.strong {{ background:#0D1F14; border:1px solid #1A3A24; border-radius:8px; padding:10px; font-size:12px; }}

.rec-card {{ background:{theme['bg_card']}; border:1px solid {theme['bg_border']}; border-radius:10px; padding:12px; margin-bottom:10px; }}
.empty {{ text-align:center; padding:64px 20px; color:{theme['text_muted']}; }}

.toggle-wrap {{ position: fixed; top: 18px; right: 24px; z-index: 9999; }}
.toggle-pill {{ width:64px; height:32px; border-radius:16px; display:flex; align-items:center; padding:3px; position:relative; }}
.toggle-pill.dark {{ background:#1a1f35; justify-content:flex-start; }}
.toggle-pill.light {{ background:#E8F4FF; border:1.5px solid #B8D4F0; justify-content:flex-end; }}
.toggle-circle {{ width:26px; height:26px; border-radius:50%; background:white; transition:all .3s; }}
.toggle-pill.light .toggle-circle {{ background:#378ADD; }}
.toggle-emoji {{ position:absolute; font-size:14px; }}
.toggle-pill.dark .toggle-emoji {{ right:7px; }}
.toggle-pill.light .toggle-emoji {{ left:7px; }}

.stButton > button {{ background:linear-gradient(90deg, #1F6FEB, #17A86A) !important; border:none !important; border-radius:10px !important; color:white !important; font-weight:700 !important; }}
.stDownloadButton > button {{ background:#0D2A1A !important; border:1px solid #3FB950 !important; color:#3FB950 !important; }}
</style>
""",
        unsafe_allow_html=True,
    )


def _toggle_button() -> None:
    if st.session_state.dark_mode:
        html = '<div class="toggle-wrap"><div class="toggle-pill dark"><div class="toggle-circle"></div><span class="toggle-emoji">🌙</span></div></div>'
        btn = "🌙"
        help_txt = "Switch to Light Mode"
    else:
        html = '<div class="toggle-wrap"><div class="toggle-pill light"><span class="toggle-emoji">☀️</span><div class="toggle-circle"></div></div></div>'
        btn = "☀️"
        help_txt = "Switch to Dark Mode"

    st.markdown(html, unsafe_allow_html=True)
    c = st.columns([10, 1])[1]
    with c:
        if st.button(btn, key="dark_toggle", help=help_txt):
            st.session_state.dark_mode = not st.session_state.dark_mode
            st.rerun()


def _color(score: int | None) -> str:
    if score is None:
        return "#30363D"
    if score >= 70:
        return "#3FB950"
    if score >= 40:
        return "#E3B341"
    return "#F85149"


def _render_scores(ats: int | None, jd: int | None, impact: int | None, overall: int | None) -> None:
    def fmt(v):
        return "--" if v is None else str(v)

    st.markdown(
        f"""
<div class="score-grid">
  <div class="score-card"><div class="score-label">ATS Score</div><div class="score-value" style="color:{_color(ats)}">{fmt(ats)}</div></div>
  <div class="score-card"><div class="score-label">JD Match %</div><div class="score-value" style="color:{_color(jd)}">{fmt(jd)}</div></div>
  <div class="score-card"><div class="score-label">Impact Score</div><div class="score-value" style="color:{_color(impact)}">{fmt(impact)}</div></div>
  <div class="score-card"><div class="score-label">Overall Score</div><div class="score-value" style="color:{_color(overall)}">{fmt(overall)}</div></div>
</div>
""",
        unsafe_allow_html=True,
    )


def _render_donut(score: int) -> None:
    value = max(0, min(100, int(score)))
    color = _color(value)
    fig = go.Figure(
        data=[
            go.Pie(
                values=[value, 100 - value],
                hole=0.72,
                marker=dict(colors=[color, "#21262D"]),
                textinfo="none",
                hoverinfo="skip",
                sort=False,
            )
        ]
    )
    fig.update_layout(
        showlegend=False,
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        annotations=[dict(text=f"<b>{value}</b>", x=0.5, y=0.5, showarrow=False, font=dict(size=26))],
        width=160,
        height=160,
    )
    st.plotly_chart(fig, use_container_width=False, config={"displayModeBar": False})


def _render_ats_bars(scores: dict) -> None:
    html = ""
    for label, val in scores.items():
        klass = "#3FB950" if val >= 70 else "#E3B341" if val >= 40 else "#F85149"
        html += (
            '<div class="ats-row">'
            + f'<span class="ats-label">{label}</span>'
            + f'<div class="ats-track"><div style="height:100%;width:{val}%;background:{klass};"></div></div>'
            + f'<span class="ats-val">{val}%</span>'
            + "</div>"
        )
    st.markdown(html, unsafe_allow_html=True)


def _render_keyword_pills(matched: list, missing: list, partial: list) -> None:
    pills = ""
    for k in matched:
        pills += f'<span class="kw match">{k}</span>'
    for k in partial:
        pills += f'<span class="kw partial">{k}</span>'
    for k in missing:
        pills += f'<span class="kw miss">{k}</span>'
    st.markdown(f'<div class="pill-wrap">{pills}</div>', unsafe_allow_html=True)


def _render_compare(issue_num: int, description: str, weak: str, strong: str) -> None:
    st.markdown(
        f"""
<div class="compare-card">
  <div style="display:flex;gap:10px;align-items:center;margin-bottom:8px;">
    <div style="width:26px;height:26px;border-radius:50%;background:#0C2D4F;color:#58A6FF;display:flex;align-items:center;justify-content:center;font-weight:700;">{issue_num}</div>
    <div style="font-weight:700;">Improvement Opportunity {issue_num}</div>
  </div>
  <div style="font-size:12px;color:#7D8590;margin-bottom:10px;">{description}</div>
  <div class="compare-grid">
    <div class="weak"><div style="font-size:10px;font-weight:700;color:#F85149;">WEAKER</div>{weak}</div>
    <div class="strong"><div style="font-size:10px;font-weight:700;color:#3FB950;">STRONGER</div>{strong}</div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )


def _resume_preview(text: str, bullet_items: list) -> None:
    colored = text
    for item in bullet_items[:40]:
        bullet = item.get("bullet", "")
        if not bullet:
            continue
        category = item.get("star", "moderate")
        if category == "strong":
            bg = "#E0FFE8"
        elif category == "weak":
            bg = "#FFE0E0"
        else:
            bg = "#FFF8E0"
        colored = colored.replace(bullet, f"<span style='background:{bg};padding:1px 2px;border-radius:2px;'>{bullet}</span>")

    st.markdown("<div class='section-label'>LIVE RESUME PREVIEW</div>", unsafe_allow_html=True)
    st.markdown(
        "<div style='background:#F8F9FA;color:#1F2328;border-radius:10px;border:1px solid #D0D7DE;padding:12px;max-height:320px;overflow:auto;white-space:pre-wrap;'>"
        + colored
        + "</div>",
        unsafe_allow_html=True,
    )


def _render_empty() -> None:
    st.markdown(
        """
<div class="empty">
  <div style="width:70px;height:70px;margin:0 auto 14px;border:2px dashed #30363D;border-radius:50%;display:flex;align-items:center;justify-content:center;">◌</div>
  <div style="font-size:16px;font-weight:700;">Ready to analyze</div>
  <div style="font-size:12px;">Upload your resume and click Analyze Resume to see your full report</div>
</div>
""",
        unsafe_allow_html=True,
    )


def _hero() -> None:
    st.markdown(
        """
<div class="hero">
  <div class="hero-title">RESKILL</div>
  <div class="hero-sub">AI-Powered Resume Analyzer — Land Your Dream Job</div>
  <div class="badge-row">
    <span class="stat-badge">⚡ Instant Analysis</span>
    <span class="stat-badge">🎯 ATS Score</span>
    <span class="stat-badge">📊 Skill Gap Report</span>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )


def _analyze(role_key: str, title: str, seniority: str, industry: str, jd_text: str, resume_text: str, filename: str) -> None:
    try:
        st.session_state.analysis_running = True
        with st.status("Processing", expanded=True) as status:
            st.write("📥 Reading file...")
            contact = extract_contact_info(resume_text)

            st.write("🔍 Extracting text and sections...")
            sections = split_sections(resume_text)

            st.write("🧠 Running AI analysis...")
            skill_results = extract_skills(resume_text, role_key, sections)
            bullet_results = analyze_bullets(sections.get("experience", ""), sections.get("projects", ""))
            ats_results = check_ats(
                resume_text,
                filename,
                skill_results.get("all_role_skills", []),
                skill_results.get("matched", []),
            )
            jd_results = match_job_description(resume_text, jd_text)

            st.write("📊 Calculating scores...")
            scores = score_resume(
                sections=sections,
                contact_score=contact.get("completeness_score", 0),
                matched_skills=skill_results.get("matched", []),
                missing_skills=skill_results.get("missing", []),
                bullet_stats=bullet_results,
            )

            weak_items = bullet_results.get("weak_bullets", [])[:5]
            rewrites = []
            for weak in weak_items:
                rewrites.append({"weak": weak, "strong": rewrite_bullet(weak, title or role_key.replace("_", " "))})

            section_tips = []
            for sec_name in ["summary", "experience", "projects"]:
                sec_text = sections.get(sec_name, "")
                if sec_text:
                    section_tips.extend(suggest_improvements(sec_name, sec_text))

            ai_summary = generate_summary(
                name=contact.get("name", "Candidate"),
                job_title=title or role_key.replace("_", " ").title(),
                years_exp="3+",
                top_skills=", ".join(skill_results.get("matched", [])[:5]) or "core technical skills",
            )

            recs = recommend_courses_and_jobs(skill_results.get("missing", []), skill_results.get("matched", []))

            st.write("✅ Generating report...")
            report_payload = {
                "candidate_name": contact.get("name") or "Candidate",
                "overall_score": scores.get("total_score", 0),
                "score_breakdown": scores.get("breakdown", {}),
                "max_points": {
                    "contact": 10,
                    "summary": 10,
                    "experience": 25,
                    "education": 15,
                    "skills": 20,
                    "projects": 10,
                    "certifications": 5,
                    "formatting": 5,
                },
                "ats_score": ats_results.get("score", 0),
                "keyword_match_rate": ats_results.get("breakdown", {}).get("keyword_match", 0),
                "ats_issues": ats_results.get("issues", []),
                "matched_skills": skill_results.get("matched", []),
                "missing_skills": skill_results.get("missing", []),
                "courses": recs.get("courses", []),
                "rewrites": rewrites,
                "section_tips": section_tips,
            }
            report_bytes = generate_pdf_report(report_payload)

            st.session_state.parsed_sections = sections
            st.session_state.scores = scores
            st.session_state.ats_results = ats_results
            st.session_state.jd_results = jd_results
            st.session_state.skill_results = skill_results
            st.session_state.bullet_results = bullet_results.get("items", [])
            st.session_state.ai_suggestions = {
                "rewrites": rewrites,
                "section_tips": section_tips,
                "summary": ai_summary,
                "recommendations": recs,
            }
            st.session_state.report_bytes = report_bytes
            st.session_state.analysis_done = True

            status.update(label="Completed", state="complete")
        st.toast("✅ Analysis complete!")
    except ParseError as exc:
        st.error(str(exc))
    except Exception:
        st.error("Something went wrong during analysis. Please try again.")
    finally:
        st.session_state.analysis_running = False


def main() -> None:
    st.set_page_config(page_title="Reskill", layout="wide")
    _init_session()
    theme = _theme_vars()
    _inject_css(theme)
    _toggle_button()

    col_input, col_results = st.columns([1, 1], gap="large")

    with col_input:
        st.markdown("<div class='panel'>", unsafe_allow_html=True)
        if not st.session_state.uploaded_filename and not st.session_state.analysis_done:
            _hero()

        st.markdown("<div class='privacy'>🛡️ Your resume data is processed locally and never stored</div>", unsafe_allow_html=True)
        with st.expander("Privacy details"):
            st.write("All analysis runs in session. No resume data is persisted externally.")

        st.markdown("<div class='section-label'>Resume + Target Role Input</div>", unsafe_allow_html=True)

        uploaded = st.file_uploader("Upload Resume", type=["pdf", "docx", "txt"], label_visibility="collapsed")
        if uploaded is not None:
            if uploaded.size > MAX_UPLOAD_BYTES:
                st.warning("File exceeds 5MB. Please upload a smaller file.")
            else:
                try:
                    parsed = parse_resume_file(uploaded.name, uploaded.getvalue())
                    st.session_state.resume_text = parsed.text[:MAX_RESUME_CHARS]
                    st.session_state.uploaded_filename = uploaded.name
                    st.caption(f"Uploaded: {uploaded.name} ({uploaded.size / 1024:.1f} KB)")
                except ParseError as exc:
                    st.error(str(exc))

        job_title = st.text_input("Target Job Title", placeholder="Example: Senior Backend Engineer")
        seniority = st.selectbox("Seniority", options=SENIORITY_OPTIONS, index=1)
        industry = st.text_input("Industry", placeholder="Fintech, Healthcare, SaaS...")
        default_role = _infer_role(job_title)

        role_labels = {
            "general_role": "General Role",
            "software_engineer": "Software Engineer",
            "data_scientist": "Data Scientist",
            "product_manager": "Product Manager",
            "devops_engineer": "DevOps Engineer",
            "designer": "Designer",
            "marketing": "Marketing",
        }
        role_key = st.selectbox(
            "Role Mapping",
            options=ROLE_MAPPING_OPTIONS,
            index=ROLE_MAPPING_OPTIONS.index(default_role) if default_role in ROLE_MAPPING_OPTIONS else 0,
            format_func=lambda k: role_labels.get(k, k),
        )

        jd_text = st.text_area(
            "Job Description (optional, for JD matching)",
            placeholder="Paste the job description here to get JD match score and missing keywords",
            max_chars=MAX_JD_CHARS,
            height=140,
        )
        st.markdown(f"<div style='text-align:right;font-size:11px;color:{theme['text_muted']};'>{len(jd_text)} / {MAX_JD_CHARS}</div>", unsafe_allow_html=True)

        resume_text = st.text_area(
            "Resume Text",
            placeholder="Paste resume content here, or upload a file above",
            value=st.session_state.resume_text,
            max_chars=MAX_RESUME_CHARS,
            height=220,
        )
        st.session_state.resume_text = resume_text
        st.markdown(f"<div style='text-align:right;font-size:11px;color:{theme['text_muted']};'>{len(resume_text)} / {MAX_RESUME_CHARS}</div>", unsafe_allow_html=True)

        analyze_clicked = st.button("Analyze Resume", disabled=st.session_state.analysis_running, use_container_width=True)
        if analyze_clicked:
            if not resume_text.strip():
                st.error("Please provide resume content or upload a file.")
                st.toast("Please add resume text", icon="⚠️")
            else:
                _analyze(
                    role_key=role_key,
                    title=job_title,
                    seniority=seniority,
                    industry=industry,
                    jd_text=jd_text,
                    resume_text=resume_text,
                    filename=st.session_state.uploaded_filename or "resume.txt",
                )

        st.markdown("</div>", unsafe_allow_html=True)

    with col_results:
        st.markdown("<div class='panel'>", unsafe_allow_html=True)
        st.markdown("<div class='section-label'>Results Dashboard</div>", unsafe_allow_html=True)

        if not st.session_state.analysis_done:
            _render_empty()
            st.markdown("</div>", unsafe_allow_html=True)
            return

        scores = st.session_state.scores
        ats = st.session_state.ats_results
        jd = st.session_state.jd_results
        skills = st.session_state.skill_results
        bullets = st.session_state.bullet_results
        ai = st.session_state.ai_suggestions

        overall = int(scores.get("total_score", 0))
        impact = int(scores.get("summary", {}).get("quantified_percentage", 0))
        jd_score = jd.get("match_score", 0) if jd else None
        _render_scores(ats.get("score", 0), jd_score, impact, overall)

        top1, top2 = st.columns([1, 2])
        with top1:
            _render_donut(overall)
        with top2:
            st.markdown("### ATS Compatibility")
            _render_ats_bars(
                {
                    "Keyword Match": int(ats.get("breakdown", {}).get("keyword_match", 0)),
                    "Formatting": int(ats.get("breakdown", {}).get("file_format", 0)),
                    "Section Headers": int(ats.get("breakdown", {}).get("section_headers", 0)),
                    "File Readability": int(ats.get("breakdown", {}).get("readability", 0)),
                }
            )

        st.markdown("### Keyword Analysis")
        _render_keyword_pills(skills.get("matched", []), skills.get("missing", []), skills.get("partial", []))

        st.markdown("### Weaker vs Stronger Bullets")
        rewrites = ai.get("rewrites", [])
        for idx, rewrite in enumerate(rewrites[:6], start=1):
            _render_compare(idx, "Improve impact and specificity", rewrite.get("weak", ""), rewrite.get("strong", ""))

        st.markdown("### Skills Coverage")
        chart_rows = []
        for sk in skills.get("matched", []):
            chart_rows.append({"skill": sk, "pct": 100, "type": "Matched"})
        for sk in skills.get("missing", []):
            chart_rows.append({"skill": sk, "pct": 30, "type": "Missing"})
        if chart_rows:
            fig = px.bar(
                chart_rows,
                x="pct",
                y="skill",
                color="type",
                orientation="h",
                color_discrete_map={"Matched": "#3FB950", "Missing": "#F85149"},
            )
            fig.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#C9D1D9"),
                xaxis_range=[0, 100],
                margin=dict(l=0, r=0, t=10, b=0),
            )
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

        _resume_preview(st.session_state.resume_text, bullets)

        st.markdown("### Course Recommendations")
        courses = ai.get("recommendations", {}).get("courses", [])
        c1, c2 = st.columns(2)
        for idx, course in enumerate(courses[:6]):
            col = c1 if idx % 2 == 0 else c2
            with col:
                st.markdown(
                    "<div class='rec-card'>"
                    + f"<div style='font-weight:700;'>{course.get('skill', '').title()}</div>"
                    + f"<div style='font-size:12px;color:{theme['text_muted']};'>{course.get('platform', '')} · {course.get('level', '')}</div>"
                    + f"<a href='{course.get('url', '#')}' target='_blank'>Open course</a>"
                    + "</div>",
                    unsafe_allow_html=True,
                )

        st.markdown("### Job Recommendations")
        for role in ai.get("recommendations", {}).get("job_roles", []):
            st.markdown(f"- {role.get('role', '').replace('_', ' ').title()} ({role.get('match', 0)}% match)")

        if ai.get("summary"):
            st.markdown("### AI Professional Summary")
            st.write(ai["summary"])

        if st.session_state.report_bytes:
            st.download_button(
                "⬇ Download Full PDF Report",
                data=st.session_state.report_bytes,
                file_name=f"reskill_report_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
                mime="application/pdf",
                use_container_width=True,
            )

        st.markdown("</div>", unsafe_allow_html=True)


if __name__ == "__main__":
    main()
