FROM python:3.13.14-slim-bookworm@sha256:9d7f287598e1a5a978c015ee176d8216435aaf335ed69ac3c38dd1bbb10e8d64

LABEL org.opencontainers.image.title="Rettungswache-Wachbuch" \
      org.opencontainers.image.description="Selbst gehostetes Wachbuch fuer Rettungswachen" \
      org.opencontainers.image.source="https://github.com/Darkspike1988/Rettungswache-Wachbuch" \
      org.opencontainers.image.licenses="AGPL-3.0-or-later" \
      org.opencontainers.image.version="0.12.0"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN groupadd --gid 10001 app && useradd --uid 10001 --gid app --create-home app

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY --chown=app:app manage.py .
COPY --chown=app:app config config
COPY --chown=app:app core core
COPY --chown=app:app scripts scripts
COPY --chown=app:app templates templates
RUN chmod 755 /app/scripts/*.sh \
    && SECRET_KEY=build-only-secret-key-not-used-at-runtime \
    DJANGO_DEBUG=true \
    DATABASE_URL=sqlite:////tmp/rwsth-build.sqlite3 \
    python manage.py collectstatic --noinput

USER app

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --start-period=30s --retries=5 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz/', timeout=3)"

CMD ["/app/scripts/start-web.sh"]
