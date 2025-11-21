ARG PYTHON_VERSION=3.12


FROM ghcr.io/astral-sh/uv:python${PYTHON_VERSION}-bookworm-slim AS builder

ARG PYTHON_VERSION
ARG NSGI_PROJ_DB_VERSION="2.1.0"

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

# Download PROJ assets early to cache them
WORKDIR /tmp/proj_assets
SHELL ["/bin/bash", "-o", "pipefail", "-c"]
RUN set -e && \
    echo "Downloading nl_nsgi_nlgeo2018.tif..." && \
    curl -fSL -o nl_nsgi_nlgeo2018.tif https://cdn.proj.org/nl_nsgi_nlgeo2018.tif && \
    echo "Downloading nl_nsgi_rdcorr2018.tif..." && \
    curl -fSL -o nl_nsgi_rdcorr2018.tif https://cdn.proj.org/nl_nsgi_rdcorr2018.tif && \
    echo "Downloading nl_nsgi_rdtrans2018.tif..." && \
    curl -fSL -o nl_nsgi_rdtrans2018.tif https://cdn.proj.org/nl_nsgi_rdtrans2018.tif && \
    echo "Fetching GitHub release info for ${NSGI_PROJ_DB_VERSION}..." && \
    release_url="https://api.github.com/repos/GeodetischeInfrastructuur/transformations/releases/tags/${NSGI_PROJ_DB_VERSION}" && \
    release_json=$(curl -fSL "$release_url") && \
    echo "Downloading bq_nsgi_bongeo2004.tif..." && \
    asset_url=$(echo "$release_json" | jq -r '.assets[] | select(.name=="bq_nsgi_bongeo2004.tif").url') && \
    curl -fSL -H "Accept: application/octet-stream" "$asset_url" -o bq_nsgi_bongeo2004.tif && \
    echo "Downloading nllat2018.gtx..." && \
    asset_url=$(echo "$release_json" | jq -r '.assets[] | select(.name=="nllat2018.gtx").url') && \
    curl -fSL -H "Accept: application/octet-stream" "$asset_url" -o nllat2018.gtx && \
    echo "Downloading proj.time.dependent.transformations.db..." && \
    asset_url=$(echo "$release_json" | jq -r '.assets[] | select(.name=="proj.time.dependent.transformations.db").url') && \
    curl -fSL -H "Accept: application/octet-stream" "$asset_url" -o proj.db && \
    echo "All downloads completed successfully!"

WORKDIR /src_app
# split install of dependencies and application in two
# for improved caching
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-editable

COPY . /src_app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-editable

# Copy downloaded PROJ assets to final location
WORKDIR /app/lib/python${PYTHON_VERSION}/site-packages/pyproj/proj_dir/share/proj/
RUN cp /tmp/proj_assets/* .

FROM python:${PYTHON_VERSION}-slim-bookworm AS runner
ARG PYTHON_VERSION
RUN groupadd -r app && \
    useradd -r -d /app -g app -N app
COPY --from=builder --chown=app:app --chmod=555 /app /app

# Place executables in the environment at the front of the path
ENV PATH="/app/bin:$PATH"
ENV PROJ_DATA="/app/lib/python${PYTHON_VERSION}/site-packages/pyproj/proj_dir/share/proj"

USER app
WORKDIR /app

# PORT for serving out API
EXPOSE 8000
# PORT for exposing health endpoints
EXPOSE 8001

ENTRYPOINT [ "ct-api" ]
