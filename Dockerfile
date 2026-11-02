FROM python:3.13-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_DATA_DIR=/data \
    APP_METRICS_PORT=9000
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && useradd --uid 10001 --create-home appuser \
    && mkdir /data && chown appuser:appuser /data
COPY --chown=appuser:appuser app.py metrics.py .
COPY --chown=appuser:appuser templates ./templates
COPY --chown=appuser:appuser static ./static
USER 10001:10001
EXPOSE 8000 9000
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "1", "--threads", "4", "--access-logfile", "-", "--error-logfile", "-", "app:create_app()"]

FROM runtime AS test
USER root
RUN pip install --no-cache-dir pytest==9.2.0
COPY --chown=appuser:appuser tests ./tests
USER 10001:10001
RUN python -m pytest tests -q

FROM runtime AS release
