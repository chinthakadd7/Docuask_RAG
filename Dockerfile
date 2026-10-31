FROM node:20-bookworm-slim AS frontend

WORKDIR /build/ui/web
COPY ui/web/package*.json ./
RUN npm ci
COPY ui/web/ ./
RUN npm run build

FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY data ./data
COPY --from=frontend /build/ui/web/dist ./ui/web/dist

EXPOSE 8000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
