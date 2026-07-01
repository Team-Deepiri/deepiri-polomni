# Polomni lab — Jupyter + API for RBLE research
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

COPY pyproject.toml poetry.lock README.md LICENSE ./
COPY src ./src
COPY tests ./tests
COPY experiments ./experiments
COPY docs ./docs
COPY scripts ./scripts
COPY data/studies ./data/studies

RUN chmod +x scripts/reproduce-p1.sh scripts/p1-gates.sh

RUN poetry install --with dev --no-ansi

EXPOSE 8091 8888

CMD ["uvicorn", "polomni.cli.commands.serve:api", "--host", "0.0.0.0", "--port", "8091"]
