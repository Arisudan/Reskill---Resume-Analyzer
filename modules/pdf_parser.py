"""File parsing utilities for PDF, DOCX, and TXT resumes with robust fallbacks."""

from __future__ import annotations

import io
import logging
import re
from dataclasses import dataclass
from typing import List, Tuple

from config import LOG_FILE


logging.basicConfig(filename=LOG_FILE, level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("reskill.pdf_parser")


@dataclass
class ParseResult:
    text: str
    pages: List[str]
    parser_used: str


class ParseError(RuntimeError):
    """Raised when a resume file cannot be parsed safely."""


def _parse_pdf_pdfplumber(raw: bytes) -> Tuple[str, List[str]]:
    import pdfplumber

    pages: List[str] = []
    with pdfplumber.open(io.BytesIO(raw)) as pdf:
        if pdf.is_encrypted:
            raise ParseError("PDF is password protected. Please remove the password and re-upload.")
        for page in pdf.pages:
            pages.append(page.extract_text() or "")
    return "\n".join(pages).strip(), pages


def _parse_pdf_pymupdf(raw: bytes) -> Tuple[str, List[str]]:
    import fitz

    doc = fitz.open(stream=raw, filetype="pdf")
    if doc.needs_pass:
        raise ParseError("PDF is password protected. Please remove the password and re-upload.")
    pages = [page.get_text("text") or "" for page in doc]
    return "\n".join(pages).strip(), pages


def _parse_pdf_ocr(raw: bytes) -> Tuple[str, List[str]]:
    import fitz
    import pytesseract
    from PIL import Image

    doc = fitz.open(stream=raw, filetype="pdf")
    ocr_pages: List[str] = []
    for page in doc:
        pix = page.get_pixmap()
        image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        ocr_pages.append(pytesseract.image_to_string(image) or "")
    return "\n".join(ocr_pages).strip(), ocr_pages


def _parse_docx(raw: bytes) -> Tuple[str, List[str]]:
    from docx import Document

    document = Document(io.BytesIO(raw))
    pages = [p.text for p in document.paragraphs if p.text.strip()]
    text = "\n".join(pages).strip()
    return text, pages


def _parse_txt(raw: bytes) -> Tuple[str, List[str]]:
    import chardet

    detected = chardet.detect(raw)
    encoding = detected.get("encoding") or "utf-8"
    text = raw.decode(encoding, errors="ignore").strip()
    return text, [text]


def extract_contact_info(text: str) -> dict:
    """Extract basic contact details and completeness score."""
    email = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)
    phone = re.search(r"(\+?\d[\d\-\s]{8,}\d)", text)
    linkedin = re.search(r"https?://(?:www\.)?linkedin\.com/\S+", text, re.IGNORECASE)
    github = re.search(r"https?://(?:www\.)?github\.com/\S+", text, re.IGNORECASE)

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    name = lines[0] if lines else ""
    location = ""
    for line in lines[:8]:
        if re.search(r"\b(city|state|country|india|usa|uk|canada|remote)\b", line, re.IGNORECASE):
            location = line
            break

    fields = {
        "name": bool(name),
        "email": bool(email),
        "phone": bool(phone),
        "linkedin": bool(linkedin),
        "github": bool(github),
        "location": bool(location),
    }
    return {
        "name": name,
        "email": email.group(0) if email else "",
        "phone": phone.group(0) if phone else "",
        "linkedin": linkedin.group(0) if linkedin else "",
        "github": github.group(0) if github else "",
        "location": location,
        "completeness_score": sum(1 for found in fields.values() if found),
    }


def parse_resume_file(filename: str, raw: bytes) -> ParseResult:
    """Parse an uploaded file and return normalized text plus per-page text list."""
    if not raw:
        raise ParseError("Could not read this file. Please try a different format.")

    lower = filename.lower()
    try:
        if lower.endswith(".pdf"):
            try:
                text, pages = _parse_pdf_pdfplumber(raw)
                if text:
                    return ParseResult(text=text, pages=pages, parser_used="pdfplumber")
            except ParseError:
                raise
            except Exception as exc:
                logger.warning("pdfplumber parse failed: %s", exc)

            try:
                text, pages = _parse_pdf_pymupdf(raw)
                if text:
                    return ParseResult(text=text, pages=pages, parser_used="pymupdf")
            except ParseError:
                raise
            except Exception as exc:
                logger.warning("pymupdf parse failed: %s", exc)

            text, pages = _parse_pdf_ocr(raw)
            if text:
                return ParseResult(text=text, pages=pages, parser_used="ocr")
            raise ParseError("Could not read this file. Please try a different format.")

        if lower.endswith(".docx"):
            text, pages = _parse_docx(raw)
            if not text:
                raise ParseError("Could not read this file. Please try a different format.")
            return ParseResult(text=text, pages=pages, parser_used="docx")

        if lower.endswith(".txt"):
            text, pages = _parse_txt(raw)
            if not text:
                raise ParseError("Could not read this file. Please try a different format.")
            return ParseResult(text=text, pages=pages, parser_used="txt")

        raise ParseError("Unsupported file type. Please upload PDF, DOCX, or TXT.")
    except ParseError:
        raise
    except Exception as exc:
        logger.exception("parse_resume_file failed")
        raise ParseError("Could not read this file. Please try a different format.") from exc
