"""Job description matcher using TF-IDF/cosine and optional semantic transformer."""

from __future__ import annotations

import logging
import re
from collections import Counter
from typing import Dict, List, Optional

import streamlit as st

from config import CACHE_TTL, LOG_FILE


logging.basicConfig(filename=LOG_FILE, level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("reskill.jd_matcher")


def _extract_keywords(text: str, top_n: int = 30) -> List[str]:
    tokens = re.findall(r"[a-zA-Z][a-zA-Z+.#-]{2,}", text.lower())
    stop = {
        "the", "and", "with", "for", "that", "this", "from", "have", "has", "will", "into", "about",
        "experience", "years", "role", "team", "work", "ability", "strong",
    }
    filtered = [t for t in tokens if t not in stop]
    counts = Counter(filtered)
    return [w for w, _ in counts.most_common(top_n)]


@st.cache_resource
def _load_sentence_transformer():
    try:
        from sentence_transformers import SentenceTransformer

        return SentenceTransformer("all-MiniLM-L6-v2")
    except Exception:
        return None


def _tfidf_similarity(resume_text: str, jd_text: str) -> Optional[int]:
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity

        vectorizer = TfidfVectorizer(stop_words="english")
        matrix = vectorizer.fit_transform([resume_text, jd_text])
        score = cosine_similarity(matrix[0:1], matrix[1:2])[0][0]
        return int(round(score * 100))
    except Exception:
        return None


def _semantic_similarity(resume_text: str, jd_text: str) -> Optional[int]:
    model = _load_sentence_transformer()
    if model is None:
        return None

    try:
        embeddings = model.encode([resume_text, jd_text], normalize_embeddings=True)
        similarity = float((embeddings[0] * embeddings[1]).sum())
        similarity = max(0.0, min(1.0, similarity))
        return int(round(similarity * 100))
    except Exception:
        return None


@st.cache_data(ttl=CACHE_TTL)
def match_job_description(resume_text: str, jd_text: str) -> Optional[Dict]:
    """Return JD match score and matched/missing JD keywords."""
    if not jd_text or not jd_text.strip():
        return None

    try:
        tfidf_score = _tfidf_similarity(resume_text, jd_text)
        semantic_score = _semantic_similarity(resume_text, jd_text)

        if semantic_score is not None:
            match_score = semantic_score
            method = "sentence-transformers"
        else:
            match_score = tfidf_score if tfidf_score is not None else 0
            method = "tfidf-cosine"

        jd_keywords = _extract_keywords(jd_text)
        resume_set = set(_extract_keywords(resume_text, top_n=120))

        matched = [kw for kw in jd_keywords if kw in resume_set]
        missing = [kw for kw in jd_keywords if kw not in resume_set]

        return {
            "match_score": int(match_score),
            "missing_jd_keywords": missing[:20],
            "matched_jd_keywords": matched[:20],
            "similarity_method": method,
        }
    except Exception:
        logger.exception("match_job_description failed")
        return {
            "match_score": 0,
            "missing_jd_keywords": [],
            "matched_jd_keywords": [],
            "similarity_method": "failed",
        }
