# Development Workflows

This document describes how to set up and run the Turret system for both Docker-based and local development.

## Prerequisites

### Common Requirements
- Git
- Python 3.11+ (for local development)
- Node.js/Bun (for frontend development)

### Docker Development Requirements
- Docker Engine 20.10+
- Docker Compose 2.0+

### Local Development Requirements
- Python virtual environment support
- Bun package manager (for frontend)

---

## Docker Development Workflow

Docker development provides isolated environments with all dependencies pre-configured. This is the recommended approach for most development scenarios.

### Initial Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd TURRET
   ```

2. **Configure secrets**
   - Copy `secrets.json.example` to `secrets.json` (if exists)
   - Or create `secrets.json` with your OpenSky credentials:
     ```json
     {
       "clientId": "your-opensky-client-id",
       "clientSecret": "your-opensky-client-secret",
       "DEFAULT_LOCATION": {
         "latitude": 41.678276,
         "longitude": 2.781306,
         "baro_altitude": 15.0
       }
     }
     ```

3. **Configure environment**
   - Copy `.env.example` to `.env` (if exists)
   - Or ensure `.env` has appropriate values:
     ```
     FLASK_ENV=development
     FLASK_DEBUG=1
     SERIAL_PORT=/dev/ttyUSB0
     NODE_ENV=development
     ```

### Running the System

#### Full Stack (Recommended)
```bash
# Start all services with development configuration
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up --build

# Or with shorter command
docker-compose -f docker-compose.dev.yml up --build
```

This starts:
- Frontend development server on port 5173 (with hot reload)
- Backend Flask server on port 5000 (with debug mode)

#### Individual Services

Start only the server:
```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up --build server
```

Start only the frontend:
```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up --build frontend
```

### Accessing the Application

- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:5000
- **API Documentation**: http://localhost:5000/api/health (health check)

### Development Commands

| Command | Description |
|---------|-------------|
| `docker-compose -f docker-compose.dev.yml up --build` | Start full dev stack |
| `docker-compose -f docker-compose.dev.yml down` | Stop all containers |
| `docker-compose -f docker-compose.dev.yml up -d --build` | Start in detached mode |
| `docker-compose -f docker-compose.dev.yml logs -f` | View logs |
| `docker-compose -f docker-compose.dev.yml logs -f server` | View server logs only |
| `docker-compose -f docker-compose.dev.yml exec server bash` | Enter server container |
| `docker-compose -f docker-compose.dev.yml restart server` | Restart server |

### Hot Reloading

- **Frontend**: Changes to files in `frontend/src/` automatically trigger rebuilds
- **Backend**: Python file changes are picked up by Flask's debug mode

### Serial Port Access

For Arduino/turret control in Docker:
1. Connect your Arduino via USB
2. Docker automatically maps `/dev/ttyACM0`, `/dev/ttyUSB0`, `/dev/ttyAMA0` to the container
3. Ensure the container has appropriate permissions (already configured in compose file)

### Debugging

#### View Logs
```bash
# All logs
docker-compose -f docker-compose.dev.yml logs -f

# Server logs only
docker-compose -f docker-compose.dev.yml logs -f server

# Frontend logs only
docker-compose -f docker-compose.dev.yml logs -f frontend
```

#### Enter Container
```bash
# Enter server container
docker-compose -f docker-compose.dev.yml exec server bash

# Enter frontend container
docker-compose -f docker-compose.dev.yml exec frontend bash
```

#### Test API Endpoints
```bash
# Health check
curl http://localhost:5000/api/health

# Get aircraft predictions
curl http://localhost:5000/api/kalman/predictions

# Get Kalman statistics
curl http://localhost:5000/api/kalman/stats
```

---

## Local Development Workflow

Local development runs services directly on your machine without Docker containers.

### Initial Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd TURRET
   ```

2. **Configure secrets**
   - Create `secrets.json` in the project root (same as Docker setup)

3. **Configure environment**
   - Create `.env` file in project root:
     ```
     FLASK_ENV=development
     FLASK_DEBUG=1
     SERIAL_PORT=/dev/ttyUSB0
     NODE_ENV=development
     ```

### Backend Setup

1. **Create virtual environment**
   ```bash
   cd server
   python -m venv local-venv
   ```

2. **Activate virtual environment**
   - Linux/Mac:
     ```bash
     source local-venv/bin/activate
     ```
   - Windows:
     ```cmd
     .\local-venv\Scripts\activate
     ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Start the server**
   ```bash
   python app.py
   ```

   The server runs on http://localhost:5000

### Frontend Setup

1. **Install Bun** (if not already installed)
   ```bash
   curl -fsSL https://bun.sh/install | bash
   ```

2. **Navigate to frontend directory**
   ```bash
   cd frontend
   ```

3. **Install dependencies**
   ```bash
   bun install
   ```

4. **Start development server**
   ```bash
   bun run dev
   ```

   The frontend runs on http://localhost:5173

### Running Both Simultaneously

Open two terminal windows:

**Terminal 1 - Backend:**
```bash
cd server
source local-venv/bin/activate
python app.py
```

**Terminal 2 - Frontend:**
```bash
cd frontend
bun run dev
```

### Development Commands

| Command | Description | Directory |
|---------|-------------|-----------|
| `python app.py` | Start backend server | server/ |
| `bun run dev` | Start frontend dev server | frontend/ |
| `bun run build` | Build frontend for production | frontend/ |

### Configuration

#### Backend Configuration
- **Port**: 5000 (default)
- **Serial Port**: Configured via `SERIAL_PORT` environment variable
- **OpenSky Credentials**: Configured in `secrets.json`

#### Frontend Configuration
- **Port**: 5173 (default)
- **API URL**: Automatically points to localhost:5000 in development
- **Environment**: Configured via `NODE_ENV` environment variable

### Serial Port Access (Local)

1. Connect Arduino via USB
2. Identify the port:
   - Linux: `/dev/ttyACM0` or `/dev/ttyUSB0`
   - Mac: `/dev/cu.usbmodemXXXX`
   - Windows: `COM3`, `COM4`, etc.
3. Update `.env` file:
   ```
   SERIAL_PORT=/dev/ttyACM0
   ```
4. Restart the server

### Debugging

#### Backend Debugging
```bash
# With debug output
FLASK_DEBUG=1 python app.py

# View all logs
python app.py 2>&1 | tee server.log
```

#### Frontend Debugging
```bash
# Run with verbose output
bun run dev --debug

# Check build
bun run build
```

#### API Testing
```bash
# Health check
curl http://localhost:5000/api/health

# List serial ports
curl http://localhost:5000/api/serial/ports

# Get aircraft data
curl -X POST http://localhost:5000/api/aircraft/position \
  -H "Content-Type: application/json" \
  -d '{"lat": 41.678, "lon": 2.781, "radius_km": 100}'

# Kalman endpoints
curl http://localhost:5000/api/kalman/predictions
curl http://localhost:5000/api/kalman/stats
```

---

## Environment Variables

### Common Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `FLASK_ENV` | development | Flask environment mode |
| `FLASK_DEBUG` | 1 | Enable Flask debug mode |
| `NODE_ENV` | development | Node.js environment mode |
| `SERIAL_PORT` | /dev/ttyUSB0 | Serial port for Arduino |
| `SERIAL_BAUDRATE` | 9600 | Serial baud rate |

### Backend Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `WERKZEUG_RUN_MAIN` | - | Set by Flask reloader |

---

## Troubleshooting

### Docker Issues

**Problem**: Permission denied for serial port
**Solution**: Add user to docker group and ensure device permissions:
```bash
sudo usermod -aG docker $USER
sudo chmod a+rw /dev/ttyUSB0
```

**Problem**: Port already in use
**Solution**: Kill existing process or use different port:
```bash
lsof -i :5000
kill <PID>
```

### Local Development Issues

**Problem**: Missing dependencies
**Solution**: Ensure all requirements are installed:
```bash
cd server
pip install -r requirements.txt

cd ../frontend
bun install
```

**Problem**: Serial port not found
**Solution**: Check connected devices:
```bash
# Linux
ls /dev/tty*

# Mac
ls /dev/cu.*

# Windows
mode
```

**Problem**: OpenSky API authentication failed
**Solution**: Verify `secrets.json` contains valid credentials:
```bash
cat secrets.json | python -m json.tool
```

### Common Fixes

| Issue | Docker Solution | Local Solution |
|-------|----------------|----------------|
| Port conflict | Change port in compose file | Change port in app.py |
| Dependency missing | Rebuild container | pip install/bun install |
| Serial not working | Check device mapping | Check .env file |
| CORS errors | Ensure CORS configured | Ensure CORS configured |

---

## Production Deployment

For production deployment, use `docker-compose.prod.yml`:

```bash
# Build and start production stack
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up --build -d
```

Note: Production mode disables debug features and uses Gunicorn for the Flask server.

---

## Comparison: Docker vs Local Development

| Aspect | Docker | Local |
|--------|--------|-------|
| Setup Complexity | Medium (initial) | Low |
| Dependency Isolation | Full | None |
| Environment Consistency | High | Medium |
| Hot Reload | Configured | Native |
| Serial Port Access | Requires mapping | Direct access |
| Performance | Slight overhead | Native speed |
| Debugging | Container logs | Direct output |
| Recommended For | Team development, CI/CD | Quick testing, single dev |
