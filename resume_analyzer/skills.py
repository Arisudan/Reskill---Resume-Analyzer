ROLE_SKILLS = {
    "data_scientist": [
        "python",
        "sql",
        "machine learning",
        "statistics",
        "pandas",
        "data visualization",
    ],
    "backend_developer": [
        "python",
        "apis",
        "sql",
        "testing",
        "docker",
        "git",
    ],
    "frontend_developer": [
        "javascript",
        "html",
        "css",
        "react",
        "testing",
        "git",
    ],
    "default": [
        "communication",
        "problem solving",
        "teamwork",
        "project management",
        "documentation",
    ],
}


ROLE_TITLE_HINTS = {
    "backend_developer": [
        "backend",
        "back end",
        "api",
        "server",
        "platform engineer",
        "python developer",
        "java developer",
        "golang",
    ],
    "frontend_developer": [
        "frontend",
        "front end",
        "ui",
        "ux",
        "react",
        "web developer",
        "javascript",
    ],
    "data_scientist": [
        "data scientist",
        "machine learning",
        "ml engineer",
        "ai engineer",
        "analytics",
        "data analyst",
        "nlp",
    ],
}


def normalize_role(role: str) -> str:
    normalized = role.strip().lower().replace(" ", "_")
    if normalized in ROLE_SKILLS:
        return normalized
    return "default"


def infer_role_from_title(title: str) -> str:
    normalized = title.strip().lower()
    if not normalized:
        return "default"

    for role, hints in ROLE_TITLE_HINTS.items():
        if any(hint in normalized for hint in hints):
            return role

    return "default"
