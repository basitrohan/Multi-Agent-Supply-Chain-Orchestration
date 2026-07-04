# =============================================================================
# Dockerfile for SupplyChain Sentinel
# =============================================================================
# This is a MULTI-STAGE build, which is the professional standard for Python
# services. Here's WHY we do it this way (good to explain in an interview):
#
#   Stage 1 ("builder"): installs build tools + compiles Python dependencies
#                         into a virtual environment.
#   Stage 2 ("runtime"):  copies ONLY the finished virtual environment + app
#                         code into a clean, slim image -- no compilers, no
#                         build caches, no leftover apt package lists.
#
# Result: a much smaller final image (faster to pull/deploy) and a smaller
# attack surface (fewer tools available inside the running container).
# =============================================================================

# ---------- Stage 1: Builder ----------
FROM python:3.12-slim AS builder

WORKDIR /build

# System packages needed only to BUILD some Python wheels (e.g. numpy/pandas
# may need a C compiler on some platforms). These never reach the final image.
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
    && rm -rf /var/lib/apt/lists/*

# Create an isolated virtual environment inside the builder stage.
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt


# ---------- Stage 2: Runtime ----------
FROM python:3.12-slim AS runtime

# Run as a non-root user -- standard security practice for production containers.
RUN groupadd -r appuser && useradd -r -g appuser appuser

WORKDIR /app

# Copy the pre-built virtual environment from the builder stage (no compilers
# or build artifacts come along with it).
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Copy application code and data.
COPY app/ ./app/
COPY data/sample/ ./data/sample/
COPY .env.example ./.env.example

# The container writes generated reports + logs here; declared as a volume
# mount point so docker-compose can persist them on the host (see docker-compose.yml).
RUN mkdir -p /app/data/reports && chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

# Basic container health check -- hits our own /api/v1/health endpoint.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/v1/health')" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
