# Development stage
FROM python:3.11-slim AS development

WORKDIR /app

# Install dependencies (requirements.txt will be mounted from host)
# We need to copy it temporarily to install
COPY server/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt && \
    rm /tmp/requirements.txt

# Create static directory (will be populated by volume mounts)
RUN mkdir -p static

# Create services directory
RUN mkdir -p services

EXPOSE 5000
CMD ["python", "app.py"]

# Production stage
FROM python:3.11-alpine AS production

# First, build the frontend using Bun
WORKDIR /frontend
COPY frontend/package.json frontend/bun.lock ./
RUN apk add --no-cache --update bun && \
    bun install --production=false
COPY frontend/ ./
RUN bun build.ts

# Now set up the Python server
WORKDIR /app
RUN apk add --no-cache gcc musl-dev libffi-dev openssl-dev

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy server application files
COPY app.py .
COPY services/ ./services/

# Copy built frontend to static directory
RUN mkdir -p static && \
    cp -r /frontend/out/* static/ && \
    cp /frontend/index.html static/ && \
    cp -r /frontend/public/* static/ 2>/dev/null || true

EXPOSE 5000
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "--timeout", "120", "app:app"]
