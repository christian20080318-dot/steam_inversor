FROM python:3.11-slim

WORKDIR /app

# Instalar dependencias del sistema requeridas para matplotlib y utilitarios
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libfreetype6-dev \
    libpng-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Crear carpetas de datos y gráficos persistentes
RUN mkdir -p /app/charts /app/knowledge

ENV PYTHONUNBUFFERED=1

CMD ["python", "main.py"]
