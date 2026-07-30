# Dockerization Plan for Turret Project

## Project Structure

```
TURRET/
├── firmware/          # PlatformIO-based Arduino firmware
│   ├── src/           # Source code (main.cpp, pins.h, etc.)
│   ├── include/       # Header files
│   ├── platformio.ini # PlatformIO configuration
│   └── test/          # Firmware tests
│
├── server/            # Flask-based web server
│   ├── app.py         # Main Flask application
│   └── requirements.txt # Python dependencies
│
└── frontend/          # React-based web interface
    ├── src/           # React source code
    ├── package.json   # Node.js dependencies
    └── vite.config.ts # Vite configuration
```

## Dockerization Strategy

### 1. Firmware Container (Development Only)

**Purpose**: Build and test the Arduino firmware in a containerized environment.

**Approach**: PlatformIO can run in Docker for development, but firmware must be flashed to hardware from the host. This container is for CI/CD and development consistency.

**Dockerfile** (`firmware/Dockerfile`):
```dockerfile
FROM python:3.11-slim

# Install PlatformIO and dependencies
RUN pip install platformio

# Copy PlatformIO configuration
WORKDIR /app
COPY platformio.ini .
COPY src/ ./src/
COPY include/ ./include/

# Default command - build the firmware
CMD ["platformio", "run"]
```

**Usage**:
```bash
# Build the firmware
docker build -t turret-firmware -f firmware/Dockerfile .
docker run -v $(pwd)/firmware:/app turret-firmware

# For flashing (requires USB device passthrough):
docker run -v $(pwd)/firmware:/app --device=/dev/ttyACM0 turret-firmware platformio run --target upload
```

**Notes**:
- Firmware cannot run in production inside a container (needs hardware access)
- Container is primarily for CI/CD pipeline and development environment consistency
- Requires `--privileged` or `--device` flags for USB access

---

### 2. Server Container (Flask Backend)

**Purpose**: Run the Flask web server that provides the API for the turret control.

**Approach**: Multi-stage build for production, single-stage for development.

**Dockerfile** (`server/Dockerfile`):
```dockerfile
# Development stage
FROM python:3.11-slim as development

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000
CMD ["python", "app.py"]

# Production stage
FROM python:3.11-alpine as production

WORKDIR /app
RUN apk add --no-cache gcc musl-dev libffi-dev openssl-dev

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "app:app"]
```

**docker-compose.yml** (for development):
```yaml
version: '3.8'
services:
  server:
    build:
      context: .
      dockerfile: server/Dockerfile
    ports:
      - "5000:5000"
    volumes:
      - ./server:/app
    environment:
      - FLASK_ENV=development
    restart: unless-stopped
```

**Usage**:
```bash
# Build and run for development
docker-compose up --build server

# Production build
docker build -t turret-server -f server/Dockerfile --target production .
docker run -p 5000:5000 turret-server
```

**Environment Variables**:
- `FLASK_ENV`: Set to "development" or "production"
- `SERIAL_PORT`: Path to the serial device (e.g., `/dev/ttyACM0`)
- `SERIAL_BAUDRATE`: Baud rate for serial communication (e.g., 115200)

**Notes**:
- For production, use Gunicorn or uWSGI as the WSGI server
- Serial port access requires `--device` flag or running on host
- Consider adding health checks and logging configuration

---

### 3. Frontend Container (React with Vite)

**Purpose**: Build and serve the React web interface.

**Approach**: Multi-stage build - build stage with Node.js, serve stage with Nginx.

**Dockerfile** (`frontend/Dockerfile`):
```dockerfile
# Build stage
FROM node:20-alpine as builder

WORKDIR /app
COPY frontend/package.json frontend/bun.lock ./
RUN npm install

COPY frontend/ ./
RUN npm run build

# Production stage
FROM nginx:alpine

# Copy built assets from builder
COPY --from=builder /app/out /usr/share/nginx/html

# Copy custom nginx config
COPY frontend/nginx.conf /etc/nginx/nginx.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

**nginx.conf** (optional, for routing API requests):
```nginx
user  nginx;
worker_processes  auto;

error_log  /var/log/nginx/error.log notice;
pid        /var/run/nginx.pid;

events {
    worker_connections  1024;
}

http {
    include       /etc/nginx/mime.types;
    default_type  application/octet-stream;

    server {
        listen 80;
        server_name localhost;

        location / {
            root   /usr/share/nginx/html;
            index  index.html index.htm;
            try_files $uri $uri/ /index.html;
        }

        location /api/ {
            proxy_pass http://server:5000/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        }
    }
}
```

**Usage**:
```bash
# Build the frontend
docker build -t turret-frontend -f frontend/Dockerfile .
docker run -p 80:80 turret-frontend
```

---

## Complete docker-compose.yml (Production)

```yaml
version: '3.8'

services:
  frontend:
    build:
      context: .
      dockerfile: frontend/Dockerfile
    ports:
      - "80:80"
    depends_on:
      - server
    restart: unless-stopped

  server:
    build:
      context: .
      dockerfile: server/Dockerfile
      target: production
    ports:
      - "5000:5000"
    environment:
      - FLASK_ENV=production
      - SERIAL_PORT=/dev/ttyACM0
      - SERIAL_BAUDRATE=115200
    devices:
      - "/dev/ttyACM0:/dev/ttyACM0"
    restart: unless-stopped

  # Optional: Firmware builder for CI/CD
  firmware:
    build:
      context: .
      dockerfile: firmware/Dockerfile
    volumes:
      - ./firmware:/app
    profiles:
      - ci
```

---

## Development docker-compose.yml

For local development with hot-reload capabilities:

**docker-compose.dev.yml**:
```yaml
version: '3.8'

services:
  frontend:
    image: node:20-alpine
    working_dir: /app
    volumes:
      - ./frontend:/app
      - /app/node_modules
    ports:
      - "5173:5173"
    command: sh -c "npm install && npm run dev"
    environment:
      - NODE_ENV=development
    profiles:
      - dev

  server:
    build:
      context: .
      dockerfile: server/Dockerfile
    working_dir: /app
    volumes:
      - ./server:/app
    ports:
      - "5000:5000"
    environment:
      - FLASK_ENV=development
      - FLASK_DEBUG=1
    depends_on:
      - frontend
    profiles:
      - dev
```

**Usage for Development**:
```bash
# Start all development services
docker-compose -f docker-compose.dev.yml up --build

# Or start individual services
docker-compose -f docker-compose.dev.yml up --build frontend
docker-compose -f docker-compose.dev.yml up --build server

# Access:
# - Frontend dev server: http://localhost:5173
# - API: http://localhost:5000/api/health
# - Hot-reload: Changes to frontend/src or server/app.py will auto-reload
```

---

## Development Workflow

### Local Development (without Docker)
1. Frontend: `cd frontend && npm run dev` (runs on port 5173)
2. Server: `cd server && python app.py` (runs on port 5000)
3. Firmware: Use PlatformIO IDE or CLI directly

### Local Development (with Docker)
```bash
# Run all services with development config
docker-compose -f docker-compose.dev.yml up --build

# Or using the auto-loaded override file
docker-compose up --build

# Access:
# - Frontend dev server: http://localhost:5173
# - API: http://localhost:5000/api/health
# - Changes auto-reload in both frontend and server
```

### Production Deployment
```bash
# Build all images
docker-compose -f docker-compose.yml -f docker-compose.prod.yml build

# Start all services
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

---

## Special Considerations

### 1. Serial Port Access
The Flask server needs to communicate with the Arduino via serial port. Options:
- Run the server container with `--device=/dev/ttyACM0` (Linux)
- Run the server directly on the host machine (not in container)
- Use a serial-over-network solution (socat, ser2net)

### 2. Firmware Deployment
Firmware must be flashed to the actual hardware. The Docker container is for:
- Consistent build environment
- CI/CD pipeline testing
- Development without local PlatformIO installation

### 3. Cross-Container Communication
- Frontend (Nginx) proxies API requests to the server container
- Use Docker's internal DNS (`server:5000`) for inter-container communication

### 4. Environment Configuration
Create a `.env` file for environment variables:
```
SERIAL_PORT=/dev/ttyACM0
SERIAL_BAUDRATE=115200
FLASK_ENV=production
```

---

## File Structure After Dockerization

```
TURRET/
├── firmware/
│   ├── Dockerfile
│   └── ...
├── server/
│   ├── Dockerfile
│   ├── app.py
│   ├── requirements.txt
│   └── .env
├── frontend/
│   ├── Dockerfile
│   ├── nginx.conf
│   └── ...
├── docker-compose.yml
├── docker-compose.dev.yml
├── docker-compose.prod.yml
└── .env
```

---

## Implementation Status

✅ **Dockerfiles Created:**
- `firmware/Dockerfile` - PlatformIO-based build environment
- `server/Dockerfile` - Multi-stage build (dev + production)
- `frontend/Dockerfile` - Bun + Nginx multi-stage build
- `frontend/nginx.conf` - Production Nginx configuration with API proxy

✅ **Docker Compose Files Created:**
- `docker-compose.yml` - Base configuration
- `docker-compose.dev.yml` - Development with hot-reload
- `docker-compose.prod.yml` - Production deployment

✅ **Configuration Files:**
- `.env` - Environment variables
- `.dockerignore` - Files to exclude from Docker builds

## Next Steps

1. Test the complete stack locally
2. Set up CI/CD pipeline (optional)
3. Configure serial port access for production

## Quick Start

**For development:**
```bash
docker-compose -f docker-compose.dev.yml up --build
# Frontend: http://localhost:5173
# API: http://localhost:5000/api/health
```

**For production:**
```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
# Frontend: http://localhost:80
# API: http://localhost:5000/api/health
```
