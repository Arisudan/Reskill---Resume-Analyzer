import re

MAX_INPUT_CHARS = 12000


NON_WORD_PATTERN = re.compile(r"[^a-z0-9\s]+")
MULTI_SPACE_PATTERN = re.compile(r"\s+")


def sanitize_and_truncate(text: str) -> tuple[str, bool]:
    sanitized = text.replace("\x00", " ").strip()
    if len(sanitized) <= MAX_INPUT_CHARS:
        return sanitized, False
    return sanitized[:MAX_INPUT_CHARS], True


def normalize_text(text: str) -> str:
    lowered = text.lower()
    no_symbols = NON_WORD_PATTERN.sub(" ", lowered)
    return MULTI_SPACE_PATTERN.sub(" ", no_symbols).strip()


def contains_phrase(haystack: str, phrase: str) -> bool:
    phrase_norm = normalize_text(phrase)
    if not phrase_norm:
        return False
    return phrase_norm in haystack
