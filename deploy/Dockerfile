FROM python:3.10-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
WORKDIR /app
COPY requirements.txt ./
COPY vendor/geoutils vendor/geoutils
RUN pip install --no-cache-dir -r requirements.txt
RUN apt-get update && apt-get install -y --no-install-recommends libexpat1 && rm -rf /var/lib/apt/lists/*
COPY ease_volume ease_volume
COPY static static
COPY data/demo_current.csv data/demo_reference.csv data/demo_boundary.geojson data/demo_metadata.json data/
COPY LICENSE NOTICE ./
RUN useradd --system --uid 10001 ease
USER 10001
CMD ["sh", "-c", "exec uvicorn ease_volume.hosted:from_environment --factory --host 0.0.0.0 --port ${PORT:-8000} --workers 1 --limit-concurrency 16 --no-access-log"]
