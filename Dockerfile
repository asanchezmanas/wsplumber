# --- Stage 1: Builder ---
FROM python:3.12-slim as builder

# Avoid .pyc files and enable unbuffered mode
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /app

# Install system dependencies for compilation
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libc6-dev \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# --- Stage 2: Runner ---
FROM python:3.12-slim as runner

WORKDIR /app

# Copy only the installed packages from builder
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH
ENV PYTHONPATH="/app/src:/app"

# Copy source code only
COPY src/ ./src/

# Configuration for Cloud Mode
ENV TRADING_MODE="PAPER"
ENV ENABLE_PAPER_TRADING="true"

# Port exposed (FastAPI)
EXPOSE 8000

# Start command
CMD ["uvicorn", "src.wsplumber.main:app", "--host", "0.0.0.0", "--port", "8000"]
