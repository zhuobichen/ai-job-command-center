# syntax=docker/dockerfile:1
"""Multi-stage Dockerfile for job-hunt."""

# ─── Build stage ──────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY pyproject.toml .
RUN pip install --no-cache-dir --user -e ".[full]"

# ─── Production stage ──────────────────────────────────────
FROM python:3.11-slim AS production

# Security: Run as non-root user
RUN groupadd --gid 1000 jobhunt && useradd --uid 1000 --gid jobhunt --shell /bin/bash jobhunt

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /root/.local /home/jobhunt/.local

# Copy application
COPY --chown=jobhunt:jobhunt src/ ./src/
COPY --chown=jobhunt:jobhunt config.example.toml ./config.toml
COPY --chown=jobhunt:jobhunt pyproject.toml .

# Set environment
ENV PATH=/home/jobhunt/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Create data directories
RUN mkdir -p /home/jobhunt/data /home/jobhunt/output /home/jobhunt/logs && \
    chown -R jobhunt:jobhunt /home/jobhunt

USER jobhunt

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)"

ENTRYPOINT ["python", "-m", "job_hunt"]
CMD ["--help"]


# ─── Development stage ─────────────────────────────────────
FROM production AS development

USER root

# Install development dependencies
RUN pip install --no-cache-dir --user -e ".[dev]"

USER jobhunt

ENTRYPOINT ["python", "-m", "job_hunt"]
CMD ["--help"]
