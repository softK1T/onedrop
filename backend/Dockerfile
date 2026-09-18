# OneDrop backend image: api, bot, worker, scheduler and migrations.
#
# Stage one builds a virtual environment. The runtime stage receives only the
# environment and application files, never a compiler or package cache.

FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

RUN apt-get update \
 && apt-get install -y --no-install-recommends build-essential \
 && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# setuptools resolves project.readme = "README.md" while installing the package.
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir .


FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app

# curl is only needed for the API health check below.
RUN apt-get update \
 && apt-get install -y --no-install-recommends curl \
 && rm -rf /var/lib/apt/lists/* \
 && useradd --uid 10001 --create-home --shell /usr/sbin/nologin onedrop

COPY --from=builder /opt/venv /opt/venv
COPY alembic.ini ./
COPY alembic ./alembic
COPY scripts ./scripts
COPY src ./src

RUN chown -R onedrop:onedrop /app
USER onedrop

EXPOSE 8000

# Compose disables this check for non-HTTP commands that reuse this image.
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD curl -fsS http://127.0.0.1:8000/api/v1/health || exit 1

CMD ["uvicorn", "onedrop.main:app", "--host", "0.0.0.0", "--port", "8000"]
