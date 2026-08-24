# System Overview

## Architecture

The Turret system is a web application that tracks airplanes, retrieves their positions from the OpenSky Network API, and computes turret movements to follow aircraft. The system uses Kalman filtering to predict aircraft positions between API calls, providing smooth, continuous tracking.

### Components

```
┌───────────────────────────────────────────────────────────────────┐
│                              TURRET SYSTEM                        │
├───────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌─────────────┐    ┌──────────────────┐    ┌─────────────────┐   │
│  │             │    │                  │    │                 │   │
│  │  Frontend   │◄──►│   Flask Server    │◄──►│    Arduino     │   │
│  │  (React/TS) │    │   (API + WS)      │    │    (Serial)    │   │
│  │             │    │                  │    │                 │   │
│  └─────────────┘    └──────────────────┘    └─────────────────┘   │
│           ▲                  ▲  ▲  ▲                     ▲        │
│           │                  │  │  │                     │        │
│  ┌────────┴────────┐       │  │ └────────────────┬───────┴──────┐ │
│  │                  │      │  │                  │              │ │
│  │   Web Browser    │      │  └──────────────┐   │   Serial Port│ │
│  │                  │      │                 │   │    (USB)     │ │
│  └──────────────────┘      │    Kalman       │   └──────────────┘ │
│                            │    Filter       │                    │
│                            │    Service      │                    │
│                            └────────┬────────┘                    │
│                                     │                             │
│                            ┌────────┴────────┐                    │
│                            │                 │                    │
│                            │  Aircraft       │                    │
│                            │  Service        │                    │
│                            │  (OpenSky API)  │                    │
│                            │                 │                    │
│                            └─────────────────┘                    │
│                                                                   │
└───────────────────────────────────────────────────────────────────┘
```

### Data Flow

1. **Aircraft Data Acquisition**
   - `AircraftService` queries OpenSky Network API every 10 seconds
   - Returns raw aircraft state data (position, velocity, altitude, etc.)
   - Data is filtered for airborne aircraft in the configured area

2. **Position Tracking & Prediction**
   - `KalmanFilterService` receives aircraft data
   - Creates/maintains Kalman filter tracks for each aircraft
   - Updates filters with new measurements
   - Predicts positions every 500ms between API calls

3. **WebSocket Streaming**
   - Real-time predictions streamed to frontend via Socket.IO
   - Heartbeat mechanism keeps connections alive
   - Frontend displays aircraft on 3D map

4. **Turret Control**
   - Frontend calculates target azimuth/elevation
   - Commands sent to Arduino via serial port
   - Arduino controls servo motors to point turret

5. **Data Capture (New)**
   - `DataCaptureService` logs all prediction frames
   - Records OpenSky data and Kalman statistics
   - Outputs to structured files for Jupyter analysis

## Service Layers

### Server Services (`server/services/`)

| Service | Responsibility | Data Flow |
|---------|---------------|-----------|
| `AircraftService` | Fetch from OpenSky API | HTTP → OpenSky |
| `KalmanFilterService` | Track & predict positions | AircraftService → Predictions |
| `DataCaptureService` | Log data for analysis | KalmanFilter + OpenSky → Files |

### Communication

- **REST API**: Flask endpoints for configuration and status
- **WebSocket**: Real-time data streaming via Socket.IO
- **Serial**: Turret control commands to Arduino

## Key Features

- **Continuous Tracking**: Kalman filters provide smooth position predictions between API updates
- **Multi-Aircraft Support**: Tracks multiple aircraft simultaneously
- **Real-time Visualization**: Frontend displays 3D aircraft positions
- **Hardware Integration**: Controls physical turret via Arduino
- **Data Analysis**: Capture files enable post-flight analysis in Jupyter

## Technology Stack

| Component | Technology |
|-----------|------------|
| Backend | Python 3.11, Flask, Flask-SocketIO |
| Frontend | React, TypeScript, Bun, Vite |
| Containerization | Docker, Docker Compose |
| Data Source | OpenSky Network API |
| Filtering | NumPy, Custom Kalman Filter |
| Hardware | Arduino, Serial Communication |
