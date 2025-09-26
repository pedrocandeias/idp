FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

RUN apt-get update && apt-get install -y --no-install-recommends build-essential \
    libcairo2 libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf-2.0-0 libffi8 fonts-dejavu-core && \
    rm -rf /var/lib/apt/lists/*

# Create non-root user for running app and celery
RUN groupadd -g 1000 app && useradd -m -u 1000 -g app -s /bin/bash app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app

RUN chmod +x /app/entrypoint.sh && chown -R app:app /app

EXPOSE 8000

USER app

CMD ["/app/entrypoint.sh"]
