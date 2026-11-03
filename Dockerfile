ARG PYTHON_VERSION=3.15
ARG UV_VERSION=0.13.7

# ------------------------------------------------------------------------------
# Build Stage
# ------------------------------------------------------------------------------
FROM python:${PYTHON_VERSION}-slim-trixie AS build
ARG PYTHON_VERSION

# Copy uv binary from official Astral image
COPY --from=ghcr.io/astral-sh/uv:0.13.7 /uv /uvx /bin/

# hadolint ignore=DL3008
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    git && rm -rf /var/lib/apt/lists/*

ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/opt/venv

WORKDIR /src_app

# 1. Install dependencies only (no dev packages) for cache efficiency
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

# 2. Install application package
COPY . /src_app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-editable

# ------------------------------------------------------------------------------
# Runtime Stage
# ------------------------------------------------------------------------------
FROM python:${PYTHON_VERSION}-slim-trixie AS runner
ARG PYTHON_VERSION

LABEL org.opencontainers.image.authors="NSGI <info@nsgi.nl>"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:${PATH}" \
    PROJ_DATA="/opt/venv/lib/python${PYTHON_VERSION}/site-packages/pyproj/proj_dir/share/proj"

# hadolint ignore=DL3008
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    libcurl3t64-gnutls \
    libtiff6 \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd -r app && \
    useradd -r -s /usr/sbin/nologin -d /nonexistent -g app -N app

# Copy virtual environment; retain root ownership so runtime cannot mutate packages
COPY --from=build --chown=root:root /opt/venv /opt/venv
RUN chmod -R a+rX /opt/venv

USER app
WORKDIR /tmp

EXPOSE 8000
EXPOSE 8001

ENTRYPOINT [ "ct-api" ]