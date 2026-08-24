# API Documentation

The Turret system provides both REST API and WebSocket endpoints for controlling the system and retrieving aircraft data.

## Base URL

- Development: `http://localhost:5000`
- Production: Depends on deployment configuration

---

## REST API Endpoints

### Health & Status

#### GET /api/health

Basic health check endpoint.

**Request:**
```
GET /api/health
```

**Response:**
```json
{
  "status": "ok",
  "message": "Turret server is running"
}
```

**Status Code:** 200 OK

---

### Turret Control

#### GET /api/turret/status

Get current turret status.

**Request:**
```
GET /api/turret/status
```

**Response:**
```json
{
  "azimuth": 0,
  "elevation": 0,
  "is_armed": false,
  "battery_level": 100
}
```

**Status Code:** 200 OK

**Note:** Currently returns mock data. Actual implementation pending.

---

#### POST /api/turret/command

Send a command to the turret.

**Request:**
```
POST /api/turret/command
Content-Type: application/json

{
  "azimuth": 45.0,
  "elevation": 30.0
}
```

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| azimuth | float | Yes | Azimuth angle in degrees |
| elevation | float | Yes | Elevation angle in degrees |

**Response:**
```json
{
  "status": "success",
  "command": "moveto 45.0 30.0",
  "azimuth": 45.0,
  "elevation": 30.0
}
```

**Status Codes:**
- 200 OK: Command sent successfully
- 400 Bad Request: Missing or invalid parameters
- 500 Internal Server Error: Serial port not connected

---

### Serial Port Management

#### GET /api/serial/ports

List available serial ports.

**Request:**
```
GET /api/serial/ports
```

**Response:**
```json
{
  "ports": ["/dev/ttyUSB0", "/dev/ttyACM0"],
  "count": 2,
  "default": "/dev/ttyUSB0",
  "connected": false
}
```

**Status Code:** 200 OK

---

#### GET /api/serial/connect

Connect to the default serial port.

**Request:**
```
GET /api/serial/connect
```

**Response:**
```json
{
  "ports": ["/dev/ttyUSB0"],
  "count": 1,
  "default": "/dev/ttyUSB0",
  "connected": true
}
```

**Status Code:** 200 OK

---

#### POST /api/serial/moveto

Send a moveto command to the serial port.

**Request:**
```
POST /api/serial/moveto
Content-Type: application/json

{
  "message": {
    "azimuth": 60.0,
    "elevation": 50.0
  }
}
```

**Response (Success):**
```json
{
  "status": "sent to serial",
  "message": {"azimuth": 60.0, "elevation": 50.0}
}
```

**Response (Error):**
```json
{
  "status": "error",
  "error": "Serial port not connected"
}
```

**Status Codes:**
- 200 OK: Command sent successfully
- 400 Bad Request: No message provided
- 500 Internal Server Error: Serial port not connected

---

### Aircraft Data

#### POST /api/aircraft/position

Get aircraft data around a specific GPS position.

**Request:**
```
POST /api/aircraft/position
Content-Type: application/json

{
  "lat": 41.678276,
  "lon": 2.781306,
  "radius_km": 100.0
}
```

**Parameters:**
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| lat | float | Yes | - | Latitude of center point |
| lon | float | Yes | - | Longitude of center point |
| radius_km | float | No | 100.0 | Search radius in kilometers |

**Response:**
```json
{
  "time": 1234567890,
  "states": [
    [
      "icao24", "callsign", "origin_country",
      1234567890, 1234567890,
      2.781306, 41.678276, 1500.0,
      false, 250.0, 45.0, 0.0,
      null, 1500.0, null, null, null, null
    ]
  ]
}
```

**Status Codes:**
- 200 OK: Data retrieved successfully
- 400 Bad Request: Missing or invalid parameters
- 500 Internal Server Error: API error

---

### Kalman Filter Endpoints

#### GET /api/kalman/predictions

Get the latest position predictions for all tracked flights.

**Request:**
```
GET /api/kalman/predictions
```

**Response:**
```json
{
  "predictions": [
    {
      "callsign": "ABC123",
      "icao": "404a3d",
      "origin_country": "France",
      "latitude": 41.678276,
      "longitude": 2.781306,
      "baro_altitude": 1500.0,
      "baro_altitude_km": 1.5,
      "velocity": 250.0,
      "true_track": 45.0,
      "vertical_rate": 0.0,
      "timestamp": 1234567890.123,
      "covariance_lat": 0.001,
      "covariance_lon": 0.001,
      "covariance_alt": 10.0,
      "state": "tracking",
      "on_ground": false,
      "callsign": "ABC123"
    }
  ],
  "count": 1,
  "timestamp": 1234567890.123
}
```

**Status Code:** 200 OK

---

#### GET /api/kalman/prediction/<callsign>

Get the latest position prediction for a specific flight.

**Request:**
```
GET /api/kalman/prediction/ABC123
```

**Response (Success):**
```json
{
  "callsign": "ABC123",
  "prediction": {
    "callsign": "ABC123",
    "icao": "404a3d",
    "origin_country": "France",
    "latitude": 41.678276,
    "longitude": 2.781306,
    "baro_altitude": 1500.0,
    "baro_altitude_km": 1.5,
    "velocity": 250.0,
    "true_track": 45.0,
    "vertical_rate": 0.0,
    "timestamp": 1234567890.123,
    "covariance_lat": 0.001,
    "covariance_lon": 0.001,
    "covariance_alt": 10.0,
    "state": "tracking",
    "on_ground": false
  }
}
```

**Response (Not Found):**
```json
{
  "status": "not_found",
  "error": "No prediction available for callsign: ABC123"
}
```

**Status Codes:**
- 200 OK: Prediction found
- 404 Not Found: No prediction for given callsign
- 500 Internal Server Error: Service error

---

#### GET /api/kalman/stats

Get statistics and status of the Kalman filter service.

**Request:**
```
GET /api/kalman/stats
```

**Response:**
```json
{
  "track_count": 5,
  "prediction_count": 5,
  "total_predictions": 1000,
  "total_measurements": 500,
  "last_data_update": 1234567890.123,
  "last_prediction": 1234567890.456,
  "data_update_interval": 10.0,
  "prediction_interval": 0.5,
  "time_since_last_update": 0.234,
  "time_since_last_prediction": 0.012,
  "data_thread_alive": true,
  "prediction_thread_alive": true
}
```

**Status Code:** 200 OK

---

#### POST /api/kalman/start

Start the Kalman filter service (background threads).

**Request:**
```
POST /api/kalman/start
```

**Response:**
```json
{
  "status": "started",
  "message": "Kalman filter service started"
}
```

**Status Codes:**
- 200 OK: Service started successfully
- 500 Internal Server Error: Service already running or other error

---

#### POST /api/kalman/stop

Stop the Kalman filter service (background threads).

**Request:**
```
POST /api/kalman/stop
```

**Response:**
```json
{
  "status": "stopped",
  "message": "Kalman filter service stopped"
}
```

**Status Codes:**
- 200 OK: Service stopped successfully
- 500 Internal Server Error: Error stopping service

---

## WebSocket Endpoints

The system uses Socket.IO for real-time WebSocket communication.

### Connection

**URL:** `/api/ws`

**Connection Example (JavaScript):**
```javascript
const socket = io('http://localhost:5000', {
  path: '/api/ws'
});

socket.on('connect', () => {
  console.log('Connected to server');
});

socket.on('disconnect', () => {
  console.log('Disconnected from server');
});
```

### Events

#### `connected`

Emitted when a client successfully connects.

**Payload:**
```
"one guy successfully connected on the server ! sid : <socket-id>"
```

---

#### `heartbeat`

Periodic heartbeat sent to all connected clients (every 5 seconds).

**Payload:**
```
<timestamp>
```

Example: `1234567890.123`

---

#### `aircraft_data`

Emitted when new aircraft data is received from OpenSky API.

**Payload:**
```json
{
  "ABC123": {
    "icao": "404a3d",
    "callsign": "ABC123",
    "origin_country": "France",
    "latitude": 41.678276,
    "longitude": 2.781306,
    "baro_altitude": 1500.0,
    "on_ground": false,
    "velocity": 250.0,
    "true_track": 45.0,
    "vertical_rate": 0.0,
    "time_position": 1234567890,
    "last_contact": 1234567890
  }
}
```

**Frequency:** Every 10 seconds (when new data is fetched from OpenSky)

---

#### `prediction_data`

Emitted when new position predictions are generated.

**Payload:**
```json
[
  {
    "callsign": "ABC123",
    "icao": "404a3d",
    "origin_country": "France",
    "latitude": 41.678276,
    "longitude": 2.781306,
    "baro_altitude": 1500.0,
    "baro_altitude_km": 1.5,
    "velocity": 250.0,
    "true_track": 45.0,
    "vertical_rate": 0.0,
    "timestamp": 1234567890.123,
    "covariance_lat": 0.001,
    "covariance_lon": 0.001,
    "covariance_alt": 10.0,
    "state": "tracking",
    "on_ground": false,
    "callsign": "ABC123"
  }
]
```

**Frequency:** Every 500ms (prediction interval)

---

## Data Capture Service Endpoints (New)

See [Data Capture Service Specification](../services/DATA_CAPTURE_SERVICE.md) for API endpoints related to the new data capture functionality.

---

## Error Responses

All error responses follow a consistent format:

```json
{
  "status": "error",
  "error": "Descriptive error message"
}
```

Common error status codes:
- 400 Bad Request: Invalid or missing parameters
- 404 Not Found: Resource not found
- 500 Internal Server Error: Server-side error

---

## Usage Examples

### Python

```python
import requests
import json

# Health check
response = requests.get('http://localhost:5000/api/health')
print(response.json())

# Get Kalman predictions
response = requests.get('http://localhost:5000/api/kalman/predictions')
data = response.json()
print(f"Tracking {data['count']} aircraft")

# Get aircraft at position
payload = {
    'lat': 41.678276,
    'lon': 2.781306,
    'radius_km': 100
}
response = requests.post(
    'http://localhost:5000/api/aircraft/position',
    json=payload
)
print(response.json())

# Send turret command
command = {
    'azimuth': 45.0,
    'elevation': 30.0
}
response = requests.post(
    'http://localhost:5000/api/turret/command',
    json=command
)
print(response.json())
```

### JavaScript (Browser)

```javascript
// REST API calls
fetch('http://localhost:5000/api/kalman/predictions')
  .then(response => response.json())
  .then(data => {
    console.log('Predictions:', data.predictions);
    console.log('Count:', data.count);
  });

// WebSocket connection
const socket = io('http://localhost:5000', { path: '/api/ws' });

socket.on('prediction_data', (predictions) => {
  console.log('New predictions:', predictions);
});

socket.on('aircraft_data', (data) => {
  console.log('New aircraft data:', data);
});
```

---

## Rate Limiting

Currently, there is no rate limiting implemented. However, consider:
- OpenSky API has its own rate limits
- Excessive requests may be throttled by the server

---

## Authentication

Currently, no authentication is required for the API endpoints. For production deployments, consider:
- Adding API key authentication
- Implementing JWT-based authentication
- Using HTTPS for secure communication
