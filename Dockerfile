# V3 Editorial System Production Dockerfile
FROM python:3.11-slim as builder

# V3 Security: Non-root user from start
RUN groupadd -r editorial && useradd -r -g editorial editorial

# Install system dependencies for build
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry (pinned)
ENV POETRY_VERSION="1.7.1"
RUN python -m pip install --no-cache-dir "poetry==${POETRY_VERSION}"

# Copy dependency files
WORKDIR /app
COPY pyproject.toml poetry.lock ./

# Configure Poetry for production
RUN poetry config virtualenvs.create true \
    && poetry config virtualenvs.in-project true \
    && poetry config installer.max-workers 10

# Install dependencies
RUN poetry install --no-dev --no-interaction --no-ansi

# Production stage
FROM python:3.11-slim as production

# V3 Security hardening
RUN groupadd -r editorial && useradd -r -g editorial editorial \
    && mkdir -p /app /var/log/editorial \
    && chown -R editorial:editorial /app /var/log/editorial

# Install runtime dependencies only
RUN apt-get update && apt-get install -y \
    libpq5 \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Install Playwright browsers (for extraction)
RUN python -m pip install playwright==1.40.0 \
    && playwright install chromium \
    && playwright install-deps chromium

# Copy virtual environment from builder
COPY --from=builder --chown=editorial:editorial /app/.venv /app/.venv

# Copy application code
WORKDIR /app
COPY --chown=editorial:editorial . .

# V3 Security: Remove unnecessary files
RUN rm -rf tests/ docs/ scripts/development/ \
    && find . -name "*.pyc" -delete \
    && find . -name "__pycache__" -type d -exec rm -rf {} + || true

# Set up environment
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH="/app" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Health check endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# V3 Security: Run as non-root
USER editorial

# Expose application port
EXPOSE 8000

# Labels for V3 compliance
LABEL org.opencontainers.image.title="Editorial System V3" \
      org.opencontainers.image.version="3.0.0-alpha1" \
      org.opencontainers.image.vendor="Editorial System" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.source="https://github.com/editorial-system/editorial-scripts-v3"

# Production entrypoint
# Run FastAPI app with uvicorn
CMD ["uvicorn", "ecc.main:app", "--host", "0.0.0.0", "--port", "8000"]
