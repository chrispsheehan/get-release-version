FROM python:3.12-slim

RUN apt-get update \
  && apt-get install -y --no-install-recommends git \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /repo

COPY get_next_version.py /app/get_next_version.py

ENTRYPOINT ["python3", "/app/get_next_version.py"]
