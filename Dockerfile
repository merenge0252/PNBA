FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PNBA_DATA_DIR=/data PNBA_HOST=0.0.0.0 PNBA_PORT=8000
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
COPY examples ./examples

RUN useradd --create-home --uid 1000 pnba && mkdir -p /data && chown pnba /data
USER pnba
VOLUME ["/data"]
EXPOSE 8000
HEALTHCHECK --interval=60s --timeout=5s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz')"
CMD ["python", "-m", "app", "serve"]
