FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    WEATHERFLOW_CONFIG=/app/config.yaml

WORKDIR /app

# Install dependencies before copying application code.
COPY requirements.txt ./

RUN python -m pip install --no-cache-dir \
    -r requirements.txt

# Copy only the files required by the pipeline.
COPY pyproject.toml config.yaml ./
COPY src/ ./src/
COPY sql/ ./sql/

RUN python -m pip install --no-cache-dir . && \
    groupadd --gid 1000 weatherflow && \
    useradd --uid 1000 --gid 1000 \
        --create-home weatherflow && \
    mkdir -p /app/data/raw \
        /app/data/processed \
        /app/data/quarantine \
        /app/logs \
        /app/docs/dq_reports && \
    chown -R weatherflow:weatherflow \
        /app/data /app/logs /app/docs

# Run the application without root privileges.
USER weatherflow

ENTRYPOINT ["python", "-m", "weatherflow"]

CMD ["run"]
