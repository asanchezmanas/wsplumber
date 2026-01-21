# Dockerfile para WS Plumber API
FROM python:3.12-slim

# Evitar que Python genere archivos .pyc y habilitar modo unbuffered
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV PYTHONPATH="/app/src:/app"

# Directorio de trabajo
WORKDIR /app

# Instalar dependencias del sistema necesarias
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libc6-dev \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements e instalar
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código fuente
COPY src/ ./src/
COPY data/ ./data/
# Nota: Los CSVs grandes de backtest deberían montarse como volúmenes o descargarse
# pero por ahora copiamos los de tests/scenarios
COPY tests/scenarios/ ./tests/scenarios/

# Puerto expuesto (FastAPI)
EXPOSE 8000

# Comando para arrancar la app
CMD ["uvicorn", "src.wsplumber.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
