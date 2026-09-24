FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
# libgl/libglib are needed by onnxruntime / OpenCV headless helpers
RUN apt-get update && apt-get install -y --no-install-recommends libglib2.0-0 libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /srv/backend
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN useradd --create-home sentinel && mkdir -p var && chown -R sentinel var
USER sentinel

EXPOSE 8000
# Models are mounted from ../models (see docker-compose.yml). Train them first:
#   docker compose run --rm backend python -m app.ml.text.train
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
