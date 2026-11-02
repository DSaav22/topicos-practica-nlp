FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements-api.txt .
RUN pip install -r requirements-api.txt

COPY src/ src/
COPY api/ api/
COPY models/pipeline.joblib models/metricas.json models/
COPY data/processed/catalogo.csv data/processed/reactivos_por_practica.csv data/processed/

RUN useradd --create-home --uid 10001 modelo
USER modelo

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/salud', timeout=3)"

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
