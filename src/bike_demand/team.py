def normalize_team_slug(team_name: str) -> str:
    if not team_name.strip():
        raise ValueError("non-whitespace")
    return "-".join(team_name.lower().split())
