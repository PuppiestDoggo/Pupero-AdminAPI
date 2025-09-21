FROM python:3.11-alpine

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
COPY Admin/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY Admin/app /app/app

EXPOSE 8010
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${ADMIN_PORT:-8010}"]
