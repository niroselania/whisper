FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py .
RUN useradd -m -u 1000 whisper && mkdir -p /models && chown whisper /models
USER whisper
EXPOSE 9000
# 1 worker: el modelo se carga una sola vez. Timeout largo por la descarga inicial.
CMD ["gunicorn", "--bind", "0.0.0.0:9000", "--workers", "1", "--threads", "2", "--timeout", "600", "app:app"]
