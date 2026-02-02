# Dockerfile.agent

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /opt/container-host-agent

# 1) Install Docker CLI + Compose plugin alongside your existing deps
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      gcc \
      python3-dev \
      libpq-dev \
      curl \
      ca-certificates \
      gnupg \
      lsb-release && \
    mkdir -p /etc/apt/keyrings && \
    curl -fsSL https://download.docker.com/linux/debian/gpg \
      | gpg --dearmor -o /etc/apt/keyrings/docker.gpg && \
    echo \
      "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
      https://download.docker.com/linux/debian \
      $(lsb_release -cs) stable" \
      > /etc/apt/sources.list.d/docker.list && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
      docker-ce-cli \
      docker-compose-plugin && \
    rm -rf /var/lib/apt/lists/*

# 2) Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 3) Copy your agent code
COPY app ./app
COPY .env ./

EXPOSE 8003

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8003"]
