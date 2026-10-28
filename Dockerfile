FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
WORKDIR /app
COPY Pipfile Pipfile.lock ./
RUN python -m pip install --no-cache-dir pipenv \
    && pipenv sync --system \
    && python -m pip uninstall -y pipenv \
    && useradd --create-home --uid 10001 orders
COPY --chown=orders:orders service ./service
COPY --chown=orders:orders wsgi.py ./
USER orders
EXPOSE 8080
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "1", "--threads", "4", "--access-logfile", "-", "--error-logfile", "-", "wsgi:app"]
