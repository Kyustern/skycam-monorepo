# Turret System Documentation

This documentation covers the development, architecture, and services of the Turret airplane tracking system.

## Table of Contents

- [System Overview](SYSTEM_OVERVIEW.md) - High-level architecture and components
- [Development Workflows](DEVELOPMENT_WORKFLOWS.md) - Docker and local development setup
- [Specifications](specs/) - Technical specifications
  - [API Documentation](specs/API_DOCUMENTATION.md) - REST and WebSocket API endpoints
  - [Data Formats](specs/DATA_FORMATS.md) - File formats and data structures
  - [Services](services/README.md) - Service specifications
    - [Aircraft Service](specs/services/AIRCRAFT_SERVICE.md) - OpenSky API integration
    - [Kalman Filter Service](specs/services/KALMAN_FILTER_SERVICE.md) - Position prediction
    - [Data Capture Service](specs/services/DATA_CAPTURE_SERVICE.md) - Data logging for analysis

## Quick Start

### Docker Development
```bash
# Start the development stack
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up --build

# Access:
# - Frontend: http://localhost:5173
# - Server API: http://localhost:5000
```

### Local Development
```bash
# Backend (server)
cd server
source local-venv/bin/activate
python app.py

# Frontend
cd frontend
bun install
bun run dev
```

## Project Structure

```
TURRET/
├── server/
│   ├── app.py                  # Flask application and API endpoints
│   ├── services/
│   │   ├── aircraft_service.py     # OpenSky API integration
│   │   ├── kalman_filter_service.py # Kalman filter tracking
│   │   └── __init__.py
│   ├── utils/
│   │   ├── logger.py              # Custom logging utilities
│   │   └── __init__.py
│   ├── socketio_instance.py      # Socket.IO configuration
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   └── ...                  # React/TypeScript frontend
│   ├── Dockerfile
│   └── Dockerfile.dev
├── docker-compose.yml
├── docker-compose.dev.yml
├── docker-compose.prod.yml
├── secrets.json                # OpenSky API credentials
└── docs/                       # Documentation (this folder)
```
