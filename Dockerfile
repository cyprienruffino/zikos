FROM node:20-slim AS frontend-builder

WORKDIR /build

COPY package.json package-lock.json* ./
RUN npm ci --ignore-scripts || npm install --ignore-scripts

COPY frontend/ ./frontend/
COPY tsconfig.json ./
RUN npm run build

FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libsndfile1 \
    fluidsynth \
    fluid-soundfont-gm \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN groupadd -r zikos && useradd -r -g zikos zikos

RUN pip install --upgrade pip setuptools wheel

# Install dependencies in their own layer, keyed only on pyproject.toml,
# so source edits don't trigger a multi-gigabyte dependency reinstall.
# Installs base deps + the "local" extra (llama-cpp-python, torch,
# transformers) so the image can run local GGUF/Transformers models.
COPY --chown=zikos:zikos pyproject.toml ./
RUN python -c "import tomllib; cfg = tomllib.load(open('pyproject.toml', 'rb'))['project']; \
deps = cfg['dependencies'] + cfg['optional-dependencies']['local']; \
open('/tmp/requirements-docker.txt', 'w').write('\n'.join(deps))" \
    && pip install -r /tmp/requirements-docker.txt \
    && rm /tmp/requirements-docker.txt

COPY --chown=zikos:zikos . .
COPY --from=frontend-builder --chown=zikos:zikos /build/frontend ./frontend

RUN pip install --no-deps .

RUN mkdir -p audio_storage midi_storage notation_storage && \
    chown -R zikos:zikos audio_storage midi_storage notation_storage

USER zikos

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["python", "run.py"]
