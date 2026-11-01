FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_DATA_DIR=/data
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && useradd --uid 10001 --create-home appuser \
    && mkdir /data && chown appuser:appuser /data
COPY --chown=appuser:appuser app.py .
COPY --chown=appuser:appuser templates ./templates
COPY --chown=appuser:appuser static ./static
USER 10001:10001
EXPOSE 8000
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "1", "--threads", "4", "--access-logfile", "-", "--error-logfile", "-", "app:create_app()"]
