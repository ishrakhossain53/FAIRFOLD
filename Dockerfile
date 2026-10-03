# ==============================================================================
# FairFold — application image
# ==============================================================================
# Specified in FAIRFOLD_Project_Architecture_and_Requirements.md §6.2. That section
# described this file as a snippet in a document; this is the file. A Dockerfile
# documented but not written is a deployment that fails on the first push to main.
#
# Added 2026-10-04.
#
# Three stages, and the middle one exists for a single reason: Node compiles the
# Tailwind stylesheet (design.md §11.2) and nothing in the running application
# needs Node. Copying node_modules into the final image would add ~300 MB and a
# package-supply-chain surface to a container whose only job is to run Django.
# ==============================================================================


# ------------------------------------------------------------------------------
# Stage 1 — frontend assets
# ------------------------------------------------------------------------------
FROM node:20-slim AS assets

WORKDIR /app

# Dependencies are copied before the source so that a change to a template — the
# common case — reuses the cached npm layer instead of reinstalling on every build.
COPY package.json package-lock.json* ./
# `npm ci` requires a lockfile. If one is absent, fall back to `npm install` rather
# than failing: a fresh clone should still produce an image, and the failure a
# missing lockfile causes (unpinned versions) is worse than the fallback.
RUN if [ -f package-lock.json ]; then npm ci --no-audit --no-fund; \
    else npm install --no-audit --no-fund; fi

# The whole tree, because tailwind.config.js `content` globs scan ./templates and
# ./**/templates. A missing template class is not an error — it is a silently
# absent rule.
COPY static/ ./static/
COPY templates/ ./templates/
COPY core/ ./core/
COPY accounts/ ./accounts/
COPY candidates/ ./candidates/
COPY employers/ ./employers/
COPY matching/ ./matching/
COPY assessments/ ./assessments/
COPY interviews/ ./interviews/
COPY notifications/ ./notifications/
COPY journey/ ./journey/
COPY api/ ./api/
COPY ai/ ./ai/
COPY tailwind.config.js ./

RUN npm run build


# ------------------------------------------------------------------------------
# Stage 2 — Python dependencies
# ------------------------------------------------------------------------------
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Requirements are copied alone so this layer is cached until a dependency
# actually changes — otherwise every source edit reinstalls PyTorch.
COPY requirements.txt ./

# `--extra-index-url` in requirements.txt points at the PyTorch CPU wheel index.
# Without it pip resolves the CUDA build, which is several gigabytes and
# contradicts the 2-4 vCPU assumption in the feasibility study.
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --prefix=/install -r requirements.txt

RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --prefix=/install gunicorn


# ------------------------------------------------------------------------------
# Stage 3 — runtime
# ------------------------------------------------------------------------------
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH=/home/fairfold/.local/bin:$PATH \
    DJANGO_SETTINGS_MODULE=config.settings.production

WORKDIR /app

# libmagic1  — python-magic wraps the system library; without it, importing the
#              resume upload path fails with a confusing "not found" error.
# clamav-daemon — clamav-client needs the socket/API definitions on Debian.
# Both are OS packages, not pip packages. Installing them via pip alone produces an
# image that starts and then fails on the first upload.
RUN apt-get update && apt-get install -y --no-install-recommends \
        libmagic1 \
        clamav-daemon \
        curl \
    && rm -rf /var/lib/apt/lists/*

# A non-root user. `useradd` needs the `--no-log-init` form here because the slim
# image has no /var/log directory for the default skeleton to write to.
RUN groupadd --system --gid 1000 fairfold \
    && useradd --system --uid 1000 --gid fairfold --no-log-init --create-home --home-dir /home/fairfold fairfold

COPY --from=builder /install /usr/local

COPY --from=assets /app/static/css/tailwind.css ./static/css/tailwind.css

# The application source is copied AFTER the dependency layer, so a source change
# does not invalidate the pip install above.
COPY manage.py pyproject.toml bandit.yaml ./
COPY config/ ./config/
COPY core/ ./core/
COPY accounts/ ./accounts/
COPY candidates/ ./candidates/
COPY employers/ ./employers/
COPY matching/ ./matching/
COPY assessments/ ./assessments/
COPY interviews/ ./interviews/
COPY notifications/ ./notifications/
COPY journey/ ./journey/
COPY api/ ./api/
COPY ai/ ./ai/
COPY templates/ ./templates/
COPY static/ ./static/
COPY tests/ ./tests/
COPY scripts/ ./scripts/

# Writable by the app user only. `media/` holds resume files; a container running
# as root leaves any file it writes owned by root, and the next deploy then fails
# on a permission error that looks like a disk problem.
RUN mkdir -p /app/media /app/staticfiles \
    && chown -R fairfold:fairfold /app/media /app/staticfiles

USER fairfold

EXPOSE 8000

# The liveness probe checks no dependency on purpose: making it verify the
# database means a brief database blip restarts every container.
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD curl -fsS http://localhost:8000/health/ || exit 1

# Bind 0.0.0.0 — mandatory inside a Compose network, and the port is published by
# Compose rather than exposed directly. bandit.yaml skips B104 for this line.
# 3 workers on a 2-4 vCPU host: one per core plus one spare, since these workers
# are I/O-bound waiting on PostgreSQL, Redis and the AI provider rather than
# CPU-bound. `--forwarded-allow-ips` matches the proxy header settings, so
# SECURE_PROXY_SSL_HEADER is honoured rather than ignored.
CMD ["gunicorn", "config.wsgi:application", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "3", \
     "--timeout", "120", \
     "--graceful-timeout", "30", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "--forwarded-allow-ips", "*"]