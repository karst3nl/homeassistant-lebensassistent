FROM python:3.12.14-slim-bookworm@sha256:392307d22300de8b5986851a12d9176dfc0fc073e65bf6523ebd7dcbeb23564e AS python-base

FROM python-base AS builder
COPY --from=ghcr.io/astral-sh/uv:0.13.6@sha256:af22a52f5eafef3d78e551599d405c02df61919d18028f0cea8eda93bc9986d0 /uv /usr/local/bin/uv
ENV UV_LINK_MODE=copy
WORKDIR /build
COPY pyproject.toml uv.lock README.md ./
COPY src ./src
RUN uv sync --locked --no-dev --no-editable --python /usr/local/bin/python --no-python-downloads

FROM python-base AS runtime
ARG BUILD_ARCH=amd64
ARG BUILD_VERSION=0.0.5
LABEL io.hass.name="Lebensassistent Alpha" \
      io.hass.description="Lokaler Lebensassistent mit Ingress" \
      io.hass.type="addon" \
      io.hass.arch="${BUILD_ARCH}" \
      io.hass.version="${BUILD_VERSION}" \
      org.opencontainers.image.source="https://github.com/karst3nl/homeassistant-lebensassistent" \
      org.opencontainers.image.version="${BUILD_VERSION}"
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
COPY --from=builder /build/.venv /opt/venv
# Der Entrypoint bereitet nur /data vor und verwirft danach UID/GID 0.
WORKDIR /data
CMD ["python", "-m", "lebensassistent.integrations.homeassistant"]
