import re


def normalize_team_slug(name: str) -> str:
    name = name.strip().lower()

    if not name:
        raise ValueError("Team name must contain non-whitespace characters")

    return re.sub(r"\s+", "-", name)