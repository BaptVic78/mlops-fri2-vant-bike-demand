# Lab 3: rerun the Lab 2 baseline in a clean environment built only from uv.lock.
FROM python:3.12.12-slim

# training_commit() calls the git binary; without it the pipeline raises OSError.
# .git is excluded from the build context, so the commit is recorded as "unavailable".
RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:0.12.24 /uv /uvx /bin/

# Use the image's Python 3.12.12 (never download another interpreter), precompile
# bytecode, and copy packages out of the build-only cache mount.
ENV UV_PYTHON_DOWNLOADS=never \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

# Dependencies first: this layer is rebuilt only when the manifests or lock change.
COPY pyproject.toml uv.lock .python-version ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-install-project

# Frozen snapshot, configuration and the files checked by preflight/tests.
COPY data/ data/
COPY configs/ configs/
COPY README.md ./
COPY .github/workflows/ci.yml .github/workflows/ci.yml
COPY reports/ reports/
COPY tests/ tests/
COPY src/ src/
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked

# Run from the built environment: no uv resync, rebuild or network at runtime.
ENV PATH="/app/.venv/bin:$PATH"

CMD ["python", "-m", "bike_demand.train", "--config", "configs/baseline.yaml"]
