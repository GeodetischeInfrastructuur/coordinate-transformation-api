ARG PYTHON_VERSION=3.12
FROM ghcr.io/astral-sh/uv:python${PYTHON_VERSION}-bookworm-slim AS builder
ARG PYTHON_VERSION

LABEL maintainer="NSGI <info@nsgi.nl>"
# ignore rule to use explicit versioning for apt packages, these become unavailable overtime, breaking the build
# hadolint ignore=DL3008
RUN apt-get update && \
    apt-get install --no-install-recommends -y \
    jq \
    curl \
    git && \
    rm -rf /var/lib/apt/lists/* /var/cache/apt/archives/*

ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PYTHON_DOWNLOADS=never \
    UV_PYTHON=python${PYTHON_VERSION} \
    UV_PROJECT_ENVIRONMENT=/app

WORKDIR /src_app
# split install of dependencies and application in two
# for improved caching
COPY pyproject.toml uv.lock ./

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-editable

COPY . /src_app

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-editable

FROM ubuntu:24.04 AS runner
ARG PYTHON_VERSION

# hadolint ignore=DL3008
RUN apt-get update && \
    apt-get install --no-install-recommends -y \
    python${PYTHON_VERSION} \
    libtiff6 \
    libcurl3t64-gnutls \
    libsqlite3-0 && \
    rm -rf /var/lib/apt/lists/* /var/cache/apt/archives/* && \
    ln -s /usr/bin/python${PYTHON_VERSION} /usr/local/bin/python${PYTHON_VERSION}

RUN groupadd -r app && \
    useradd -r -d /app -g app -N app
COPY --from=builder --chown=app:app --chmod=555 /app /app

# Place executables in the environment at the front of the path
ENV PATH="/app/bin:$PATH"

USER app
WORKDIR /app

# PORT for serving out API
EXPOSE 8000
# PORT for exposing health endpoints
EXPOSE 8001

ENTRYPOINT [ "ct-api" ]
