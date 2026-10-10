# UNTESTED: written without access to Docker. `make run` is the supported way to run the app.
FROM node:22-slim AS frontend
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
COPY docs/openapi.json /app/docs/openapi.json
RUN npm run build

FROM python:3.11-slim
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg libsndfile1 && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.lock.txt ./
RUN pip install --no-cache-dir -r requirements.lock.txt
COPY bpmkey/ bpmkey/
COPY backend/ backend/
COPY --from=frontend /app/frontend/dist frontend/dist
ENV PYTHONPATH=/app:/app/backend \
    DB_PATH=/data/vinyl.db AUDIO_DIR=/audio VAULT_DIR=/vault FRONTEND_DIST=/app/frontend/dist
WORKDIR /app/backend
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
