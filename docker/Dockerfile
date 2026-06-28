# Omnifold lab — Jupyter + API for RBLE research
FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    POETRY_VERSION=1.8.3 \
    POETRY_VIRTUALENVS_CREATE=false \
    POETRY_NO_INTERACTION=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    libcfitsio-dev \
    libhealpix-cxx-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir "poetry==${POETRY_VERSION}"

WORKDIR /app

COPY pyproject.toml README.md LICENSE ./
COPY omnifold_core ./omnifold_core
COPY omnifold_neural ./omnifold_neural
COPY omnifold_observatory ./omnifold_observatory
COPY omnifold_uqe_bridge ./omnifold_uqe_bridge
COPY omnifold_cli ./omnifold_cli
COPY visualization ./visualization
COPY tests ./tests
COPY experiments ./experiments
COPY docs ./docs

RUN poetry install --with dev --no-ansi

EXPOSE 8091 8888

CMD ["uvicorn", "omnifold_cli.commands.serve:api", "--host", "0.0.0.0", "--port", "8091"]
