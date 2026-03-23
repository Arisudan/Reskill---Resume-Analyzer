"""Generates a multi-page PDF report for resume analysis using fpdf2."""

from __future__ import annotations

import io
import logging
from datetime import datetime
from typing import Dict, List

from config import LOG_FILE


logging.basicConfig(filename=LOG_FILE, level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("reskill.report_generator")


def _draw_title(pdf, title: str):
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(26, 78, 168)
    pdf.cell(0, 10, title, new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(0, 0, 0)


def generate_pdf_report(report_payload: Dict) -> bytes:
    """Return PDF report bytes with 4 pages and structured sections."""
    try:
        from fpdf import FPDF

        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=12)

        # Page 1
        pdf.add_page()
        _draw_title(pdf, "Reskill Analysis Report")
        pdf.set_font("Helvetica", "", 11)
        pdf.cell(0, 8, f"Candidate: {report_payload.get('candidate_name', 'Unknown')}", new_x="LMARGIN", new_y="NEXT")
        pdf.cell(0, 8, f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)

        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 8, "Score Breakdown", new_x="LMARGIN", new_y="NEXT")

        breakdown = report_payload.get("score_breakdown", {})
        max_points = report_payload.get("max_points", {})
        pdf.set_font("Helvetica", "", 10)
        for key, value in breakdown.items():
            max_val = max_points.get(key, "-")
            pdf.cell(0, 7, f"- {key.title()}: {value} / {max_val}", new_x="LMARGIN", new_y="NEXT")

        pdf.ln(4)
        pdf.set_font("Helvetica", "B", 16)
        pdf.cell(0, 10, f"Overall Score: {report_payload.get('overall_score', 0)} / 100", new_x="LMARGIN", new_y="NEXT")

        # Page 2
        pdf.add_page()
        _draw_title(pdf, "ATS Report")
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 8, f"ATS Score: {report_payload.get('ats_score', 0)}", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(0, 8, f"Keyword Match Rate: {report_payload.get('keyword_match_rate', 0)}%", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 8, "Issues & Fix Suggestions", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 10)
        for issue in report_payload.get("ats_issues", []):
            pdf.multi_cell(0, 6, f"- {issue}")

        # Page 3
        pdf.add_page()
        _draw_title(pdf, "Skill Gap Analysis")
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 8, "Matched Skills", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 10)
        pdf.multi_cell(0, 6, ", ".join(report_payload.get("matched_skills", [])) or "None")
        pdf.ln(2)
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 8, "Missing Skills", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 10)
        pdf.multi_cell(0, 6, ", ".join(report_payload.get("missing_skills", [])) or "None")
        pdf.ln(2)
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 8, "Top Recommended Courses", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 10)
        for course in report_payload.get("courses", [])[:5]:
            pdf.multi_cell(0, 6, f"- {course.get('skill', '').title()}: {course.get('course', '')} ({course.get('platform', '')})")

        # Page 4
        pdf.add_page()
        _draw_title(pdf, "Improvement Tips")
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 8, "Top Bullet Rewrites", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 10)
        for rewrite in report_payload.get("rewrites", [])[:5]:
            pdf.multi_cell(0, 6, f"Original: {rewrite.get('weak', '')}")
            pdf.multi_cell(0, 6, f"Improved: {rewrite.get('strong', '')}")
            pdf.ln(1)

        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 8, "Section-Level Suggestions", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 10)
        for tip in report_payload.get("section_tips", [])[:8]:
            pdf.multi_cell(0, 6, f"- {tip}")

        output = io.BytesIO()
        output.write(pdf.output(dest="S").encode("latin-1"))
        return output.getvalue()
    except Exception:
        logger.exception("generate_pdf_report failed")
        return b""
