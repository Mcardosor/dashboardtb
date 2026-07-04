# ── Stage único — python:3.11-slim ────────────────────────────────────────────
FROM python:3.11-slim

WORKDIR /app

# Dependências de sistema mínimas:
#   curl  → healthcheck
#   libgomp1 → DuckDB (paralelismo de threads)
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
        libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Instala dependências Python primeiro (layer cacheável)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia código-fonte e dados de produção
# O .dockerignore exclui: raw parquets (~103 MB), scripts/, docs/, .env, __pycache__
COPY app.py .
COPY src/ src/
COPY dados_dashboard/ dados_dashboard/
COPY spec/ spec/
COPY .streamlit/ .streamlit/

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl --fail http://localhost:8501/cenarios/tb/_stcore/health || exit 1

ENTRYPOINT ["streamlit", "run", "app.py", \
    "--server.port=8501", \
    "--server.address=0.0.0.0", \
    "--server.headless=true", \
    "--server.enableCORS=false", \
    "--server.enableXsrfProtection=true", \
    "--server.maxMessageSize=200", \
    "--server.maxUploadSize=50", \
    "--browser.gatherUsageStats=false"]
