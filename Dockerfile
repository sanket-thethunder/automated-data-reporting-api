# ── Build stage ───────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /app

# Install system dependencies (ReportLab needs a C compiler)
RUN apt-get update && apt-get install -y --no-install-recommends gcc && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir --prefix=/install -r requirements.txt


# ── Runtime stage ─────────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application source
COPY app/ ./app/

# Create temp directories used by the app
RUN mkdir -p /tmp/report_gen/uploads /tmp/report_gen/outputs

# Non-root user for security
RUN useradd --create-home appuser && chown -R appuser /app /tmp/report_gen
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
