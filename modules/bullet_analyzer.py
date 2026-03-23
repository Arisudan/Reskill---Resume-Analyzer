"""Analyzes resume bullets for strength, quantification, STAR quality, repetition, and tense."""

from __future__ import annotations

import logging
import re
from collections import Counter
from typing import Dict, List

from config import LOG_FILE, STRONG_VERBS, WEAK_VERBS


logging.basicConfig(filename=LOG_FILE, level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("reskill.bullet_analyzer")


def _extract_bullets(text: str) -> List[str]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    bullets = [line.lstrip("-*• ").strip() for line in lines if line.startswith(("-", "*", "•"))]
    if bullets:
        return bullets
    return [line for line in lines if len(line.split()) >= 6][:40]


def analyze_bullets(experience_text: str, project_text: str) -> Dict:
    """Return detailed bullet-level diagnostics."""
    try:
        text = f"{experience_text}\n{project_text}".strip()
        bullets = _extract_bullets(text)

        results: List[Dict] = []
        quantified = 0
        weak_items: List[str] = []
        strong_items: List[str] = []

        for bullet in bullets:
            lower = bullet.lower()
            weak_match = next((verb for verb in WEAK_VERBS if lower.startswith(verb) or verb in lower), "")
            strong_match = next((verb for verb in STRONG_VERBS if lower.startswith(verb) or verb in lower), "")
            has_metric = bool(re.search(r"\b\d+(%|x|k|m|\+|\$)?\b", bullet))
            if has_metric:
                quantified += 1

            if weak_match:
                weak_items.append(bullet)
            if strong_match and has_metric:
                strong_items.append(bullet)

            star_score = 0
            if strong_match:
                star_score += 1
            if len(bullet.split()) >= 8:
                star_score += 1
            if has_metric:
                star_score += 1

            if star_score >= 3:
                strength = "strong"
            elif star_score == 2:
                strength = "moderate"
            else:
                strength = "weak"

            suggested_verb = "led"
            if weak_match:
                suggested_verb = {
                    "helped": "delivered",
                    "assisted": "implemented",
                    "worked on": "built",
                    "was responsible for": "owned",
                    "in charge of": "managed",
                    "participated": "executed",
                    "contributed to": "developed",
                    "supported": "enabled",
                }.get(weak_match, "led")

            tense_flag = "ok"
            if re.search(r"\b(is|are|manage|build|lead)\b", lower) and re.search(r"\b(ed|was|were)\b", lower):
                tense_flag = "mixed_tense"

            results.append(
                {
                    "bullet": bullet,
                    "weak_verb": weak_match,
                    "suggested_verb": suggested_verb,
                    "quantified": has_metric,
                    "star": strength,
                    "tense": tense_flag,
                }
            )

        words = re.findall(r"[a-zA-Z]{4,}", " ".join(bullets).lower())
        repetition = Counter(words)
        repeated = [{"word": w, "count": c} for w, c in repetition.items() if c >= 4][:12]

        total = max(1, len(bullets))
        quantified_percentage = int(round((quantified / total) * 100))

        return {
            "items": results,
            "weak_bullets": weak_items[:8],
            "strong_bullets": strong_items[:8],
            "quantified_percentage": quantified_percentage,
            "repetition": repeated,
            "total_bullets": len(bullets),
        }
    except Exception:
        logger.exception("analyze_bullets failed")
        return {
            "items": [],
            "weak_bullets": [],
            "strong_bullets": [],
            "quantified_percentage": 0,
            "repetition": [],
            "total_bullets": 0,
        }
