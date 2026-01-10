# Use official Python lightweight image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/src:.

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir uvicorn fastapi psutil

# Copy source code and data
COPY src/ ./src/
# We include some sample data if needed, but usually it comes from volumes or external URLs
# For now, we copy the project root scripts that might be needed
COPY scripts/ ./scripts/

# Expose the application port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "wsplumber.infrastructure.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
