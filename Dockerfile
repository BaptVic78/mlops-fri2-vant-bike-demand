FROM python:3.12.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.12.24 /uv /uvx /bin/

# Never download another Python at build or run time. The base image is the pin.
ENV UV_PYTHON_DOWNLOADS=never \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Lock and manifest before the source, so a code edit does not reinstall dependencies.
COPY pyproject.toml uv.lock .python-version ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-install-project

COPY src ./src
COPY tests ./tests
COPY configs ./configs
COPY data ./data
COPY .github/workflows/ci.yml .github/workflows/ci.yml
COPY README.md ./
COPY reports/week-01-team.md reports/week-01-team.md
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked

# Call the environment built above. `uv run` would sync again on every start.
CMD [".venv/bin/python", "-m", "bike_demand.train", "--config", "configs/baseline.yaml"]
