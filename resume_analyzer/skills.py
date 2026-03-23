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


def normalize_role(role: str) -> str:
    normalized = role.strip().lower().replace(" ", "_")
    if normalized in ROLE_SKILLS:
        return normalized
    return "default"
