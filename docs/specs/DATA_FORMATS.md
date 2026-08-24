# Data Formats Reference

This document describes all data formats used in the Turret system, including API responses, WebSocket messages, and file formats.

---

## Table of Contents

- [OpenSky API Data Format](#opensky-api-data-format)
- [Kalman Filter Data Formats](#kalman-filter-data-formats)
- [WebSocket Message Formats](#websocket-message-formats)
- [REST API Response Formats](#rest-api-response-formats)
- [Capture File Format (HDF5)](#capture-file-format-hdf5)

---

## OpenSky API Data Format

### Raw Response from OpenSky

The OpenSky Network API returns aircraft states in a specific format:

```json
{
  "time": 1724000000,
  "states": [
    [
      "404a3d",           // 0: ICAO24 address (hex string)
      "ABC123",           // 1: Callsign (string)
      "France",           // 2: Country of origin (string)
      1724000000,          // 3: Unix timestamp of position (seconds)
      1724000000,          // 4: Unix timestamp of last contact (seconds)
      2.781306,            // 5: Longitude (decimal degrees)
      41.678276,           // 6: Latitude (decimal degrees)
      1500.0,              // 7: Barometric altitude (meters)
      false,               // 8: On ground (boolean)
      250.0,               // 9: Velocity (m/s)
      45.0,                // 10: True track/heading (degrees from north)
      0.0,                 // 11: Vertical rate (m/s, positive = climbing)
      null,                // 12: Number of position reports (integer or null)
      1500.0,              // 13: Geometric altitude (meters)
      null,                // 14: Squawk code (integer or null)
      null,                // 15: SPI (Special Purpose Indicator, boolean or null)
      null                 // 16: Position source (integer or null)
    ]
  ]
}
```

### Parsed Flight Data (Internal)

The `AircraftService` parses OpenSky data into a dictionary format:

```python
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
    "time_position": 1724000000,
    "last_contact": 1724000000,
    "sensors": null,
    "geo_altitude": 1500.0,
    "squawk": null,
    "spi": null,
    "position_source": null
  }
}
```

---

## Kalman Filter Data Formats

### FlightPrediction (Dataclass)

The primary output of the Kalman filter service:

```python
{
  "callsign": "ABC123",
  "icao": "404a3d",
  "origin_country": "France",
  "latitude": 41.678276,
  "longitude": 2.781306,
  "baro_altitude": 1500.0,
  "baro_altitude_km": 1.5,           # Derived: baro_altitude / 1000
  "velocity": 250.0,
  "true_track": 45.0,
  "vertical_rate": 0.0,
  "timestamp": 1724000000.123,      # Unix timestamp with milliseconds
  "covariance_lat": 0.001,           # Position uncertainty (degrees^2)
  "covariance_lon": 0.001,
  "covariance_alt": 10.0,            # Altitude uncertainty (meters^2)
  "state": "tracking",               # "initializing", "tracking", or "lost"
  "on_ground": false
}
```

### FlightTrack (Internal)

The internal Kalman filter state for each aircraft:

```python
FlightTrack(
  callsign="ABC123",
  icao="404a3d",
  origin_country="France",
  state_vector=np.array([
    0.0,    # north position (meters relative to reference)
    0.0,    # east position (meters relative to reference)
    1500.0, # altitude (meters)
    100.0,  # north velocity (m/s)
    100.0,  # east velocity (m/s)
    0.0     # vertical velocity (m/s)
  ]),
  covariance_matrix=np.array([  # 6x6 matrix
    [1000.0, 0, 0, 0, 0, 0],      # Position uncertainties
    [0, 1000.0, 0, 0, 0, 0],
    [0, 0, 1000.0, 0, 0, 0],
    [0, 0, 0, 100.0, 0, 0],      # Velocity uncertainties
    [0, 0, 0, 0, 100.0, 0],
    [0, 0, 0, 0, 0, 100.0]
  ]),
  ref_latitude=41.678276,
  ref_longitude=2.781306,
  last_measurement_time=1724000000.0,
  filter_state=KalmanFilterState.TRACKING,
  Q=np.eye(6),    # Process noise covariance
  R=np.eye(3),    # Measurement noise covariance
  last_prediction_time=1724000000.0,
  predictions=[]   # List of FlightPrediction objects
)
```

### Kalman Filter Statistics

```python
{
  "track_count": 5,                      # Current number of tracked flights
  "prediction_count": 5,                # Number of predictions in latest frame
  "total_predictions": 1000,             # Total predictions generated
  "total_measurements": 500,            # Total measurements received
  "last_data_update": 1724000000.123,   # Timestamp of last data update
  "last_prediction": 1724000000.456,    # Timestamp of last prediction
  "data_update_interval": 10.0,          # Configured update interval (seconds)
  "prediction_interval": 0.5,           # Configured prediction interval (seconds)
  "time_since_last_update": 0.234,      # Seconds since last data update
  "time_since_last_prediction": 0.012, # Seconds since last prediction
  "data_thread_alive": true,             # Data update thread status
  "prediction_thread_alive": true       # Prediction thread status
}
```

---

## WebSocket Message Formats

### Connection Events

#### `connected`

Emitted when a client connects to the WebSocket server.

```
"one guy successfully connected on the server ! sid : <socket-id>"
```

Type: `string`

---

#### `disconnect`

Emitted when a client disconnects from the WebSocket server.

```
"Client disconnected: <socket-id>"
```

Type: `string`

---

### Data Events

#### `heartbeat`

Periodic heartbeat sent to all connected clients (every 5 seconds).

```
1724000000.123
```

Type: `float` (Unix timestamp with milliseconds)

---

#### `aircraft_data`

Sent when new aircraft data is received from OpenSky API (every 10 seconds).

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
    "time_position": 1724000000,
    "last_contact": 1724000000
  },
  "DEF456": {
    "icao": "404b5e",
    "callsign": "DEF456",
    "origin_country": "Germany",
    "latitude": 41.680000,
    "longitude": 2.785000,
    "baro_altitude": 1800.0,
    "on_ground": false,
    "velocity": 200.0,
    "true_track": 30.0,
    "vertical_rate": 5.0,
    "time_position": 1724000000,
    "last_contact": 1724000000
  }
}
```

Type: `Dict[str, Dict]` - Dictionary of callsign to flight data

---

#### `prediction_data`

Sent when new position predictions are generated (every 500ms).

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
    "timestamp": 1724000000.456,
    "covariance_lat": 0.001,
    "covariance_lon": 0.001,
    "covariance_alt": 10.0,
    "state": "tracking",
    "on_ground": false,
    "callsign": "ABC123"
  },
  {
    "callsign": "DEF456",
    "icao": "404b5e",
    "origin_country": "Germany",
    "latitude": 41.680000,
    "longitude": 2.785000,
    "baro_altitude": 1800.0,
    "baro_altitude_km": 1.8,
    "velocity": 200.0,
    "true_track": 30.0,
    "vertical_rate": 5.0,
    "timestamp": 1724000000.456,
    "covariance_lat": 0.002,
    "covariance_lon": 0.002,
    "covariance_alt": 15.0,
    "state": "tracking",
    "on_ground": false,
    "callsign": "DEF456"
  }
]
```

Type: `List[Dict]` - List of prediction dictionaries

---

## REST API Response Formats

### Health & Status

#### `/api/health`

```json
{
  "status": "ok",
  "message": "Turret server is running"
}
```

---

#### `/api/turret/status`

```json
{
  "azimuth": 0.0,
  "elevation": 0.0,
  "is_armed": false,
  "battery_level": 100
}
```

---

### Serial Port

#### `/api/serial/ports`

```json
{
  "ports": ["/dev/ttyUSB0", "/dev/ttyACM0"],
  "count": 2,
  "default": "/dev/ttyUSB0",
  "connected": false
}
```

---

#### `/api/serial/connect`

```json
{
  "ports": ["/dev/ttyUSB0"],
  "count": 1,
  "default": "/dev/ttyUSB0",
  "connected": true
}
```

---

#### `/api/serial/moveto` (POST)

**Success:**
```json
{
  "status": "sent to serial",
  "message": {"azimuth": 60.0, "elevation": 50.0}
}
```

**Error:**
```json
{
  "status": "error",
  "error": "Serial port not connected"
}
```

---

### Aircraft Data

#### `/api/aircraft/position` (POST)

```json
{
  "time": 1724000000,
  "states": [
    [
      "404a3d", "ABC123", "France",
      1724000000, 1724000000,
      2.781306, 41.678276, 1500.0,
      false, 250.0, 45.0, 0.0,
      null, 1500.0, null, null, null, null
    ],
    [
      "404b5e", "DEF456", "Germany",
      1724000000, 1724000000,
      2.785000, 41.680000, 1800.0,
      false, 200.0, 30.0, 5.0,
      null, 1800.0, null, null, null, null
    ]
  ]
}
```

---

### Kalman Filter Endpoints

#### `/api/kalman/predictions`

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
      "timestamp": 1724000000.456,
      "covariance_lat": 0.001,
      "covariance_lon": 0.001,
      "covariance_alt": 10.0,
      "state": "tracking",
      "on_ground": false,
      "callsign": "ABC123"
    }
  ],
  "count": 1,
  "timestamp": 1724000000.456
}
```

---

#### `/api/kalman/prediction/<callsign>`

**Success:**
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
    "timestamp": 1724000000.456,
    "covariance_lat": 0.001,
    "covariance_lon": 0.001,
    "covariance_alt": 10.0,
    "state": "tracking",
    "on_ground": false
  }
}
```

**Not Found:**
```json
{
  "status": "not_found",
  "error": "No prediction available for callsign: ABC123"
}
```

---

#### `/api/kalman/stats`

```json
{
  "track_count": 2,
  "prediction_count": 2,
  "total_predictions": 1000,
  "total_measurements": 500,
  "last_data_update": 1724000000.123,
  "last_prediction": 1724000000.456,
  "data_update_interval": 10.0,
  "prediction_interval": 0.5,
  "time_since_last_update": 0.234,
  "time_since_last_prediction": 0.012,
  "data_thread_alive": true,
  "prediction_thread_alive": true
}
```

---

#### `/api/kalman/start` (POST)

```json
{
  "status": "started",
  "message": "Kalman filter service started"
}
```

---

#### `/api/kalman/stop` (POST)

```json
{
  "status": "stopped",
  "message": "Kalman filter service stopped"
}
```

---

## Capture File Format (HDF5)

The Data Capture Service stores data in HDF5 format with the following structure:

### File Structure

```
root/
├── metadata/                    # Capture session metadata
│   ├── capture_start           # float: Unix timestamp
│   ├── capture_end             # float: Unix timestamp
│   ├── session_id              # str: UUID
│   ├── kalman_config           # dict: Filter parameters
│   ├── location                # dict: Default location
│   └── turret_version          # str: Version
├── frames/                     # Frame-level data
│   ├── timestamps              # 1D array[float]: Frame timestamps
│   ├── frame_indices           # 1D array[int]: Frame numbers
│   └── predictions/            # Prediction data per frame
│       ├── callsigns           # 1D array[str]: Callsigns per frame
│       ├── count                # 1D array[int]: Prediction count per frame
│       └── <callsign>/         # Per-flight prediction data
│           ├── positions        # 2D array[N,3]: (lat, lon, alt)
│           ├── velocities       # 2D array[N,3]: (v_north, v_east, v_alt)
│           ├── covariances      # 2D array[N,3]: (cov_lat, cov_lon, cov_alt)
│           ├── headings         # 1D array[float]: true_track
│           ├── speeds           # 1D array[float]: velocity
│           ├── states           # 1D array[str]: filter state
│           └── timestamps        # 1D array[float]: prediction timestamps
├── opensky/                    # OpenSky data
│   ├── timestamps              # 1D array[float]: Frame timestamps
│   └── <callsign>/            # Per-flight OpenSky data
│       ├── positions          # 2D array[N,3]: (lat, lon, alt)
│       ├── velocities         # 2D array[N,3]: (v_north, v_east, v_alt)
│       ├── baro_altitudes      # 1D array[float]: barometric altitude
│       ├── on_ground           # 1D array[bool]: on ground status
│       └── timestamps          # 1D array[float]: data timestamps
└── statistics/                 # Kalman filter statistics
    ├── timestamps              # 1D array[float]: Frame timestamps
    ├── track_count             # 1D array[int]: Number of tracked flights
    ├── prediction_count        # 1D array[int]: Predictions per frame
    ├── total_predictions       # 1D array[int]: Running total
    ├── total_measurements      # 1D array[int]: Running total
    ├── data_update_interval    # 1D array[float]: Configured interval
    └── prediction_interval      # 1D array[float]: Configured interval
```

### Data Types

| Field | Data Type | Description |
|-------|-----------|-------------|
| timestamps | float64 | Unix timestamp with milliseconds |
| positions | float64[3] | (latitude, longitude, altitude) in degrees, degrees, meters |
| velocities | float64[3] | (v_north, v_east, v_alt) in m/s |
| covariances | float64[3] | (cov_lat, cov_lon, cov_alt) in degrees^2, degrees^2, meters^2 |
| headings | float64 | True track in degrees from north |
| speeds | float64 | Velocity magnitude in m/s |
| states | string | Filter state: "initializing", "tracking", "lost" |
| callsigns | string | Aircraft callsign |
| on_ground | bool | Whether aircraft is on ground |

### Python Access Example

```python
import h5py
import numpy as np

# Open capture file
with h5py.File('captures/2026-08-22/14-30-00_session_001.h5', 'r') as f:
    # Access metadata
    session_id = f['metadata'].attrs['session_id']
    kalman_config = f['metadata'].attrs['kalman_config']
    
    # Access prediction data for a specific flight
    if 'frames/predictions/ABC123' in f:
        flight_group = f['frames/predictions/ABC123']
        positions = flight_group['positions'][:]  # Shape: (N, 3)
        timestamps = flight_group['timestamps'][:]
        
        # positions is a numpy array where:
        # positions[i, 0] = latitude of i-th point
        # positions[i, 1] = longitude of i-th point
        # positions[i, 2] = altitude of i-th point
    
    # Access statistics
    stats_timestamps = f['statistics/timestamps'][:]
    track_counts = f['statistics/track_count'][:]
```

---

## Error Response Format

All error responses follow a consistent format:

```json
{
  "status": "error",
  "error": "Descriptive error message"
}
```

Common error types:
- `400 Bad Request`: Invalid or missing parameters
- `404 Not Found`: Resource not found
- `500 Internal Server Error`: Server-side error

---

## Unit Conversions

### Position
- **Latitude/Longitude**: Decimal degrees (WGS84)
- **Altitude**: Meters above mean sea level (barometric)

### Velocity
- **m/s**: Meters per second (standard unit in system)
- **Knots**: 1 knot = 0.514444 m/s
- **km/h**: 1 km/h = 0.277778 m/s

### Altitude
- **Meters**: Standard unit
- **Feet**: 1 meter = 3.28084 feet
- **Flight Level**: FL100 = 10,000 feet = 3048 meters

### Heading
- **Degrees**: 0-360 degrees from north (0 = north, 90 = east, 180 = south, 270 = west)
- **Radians**: Used internally for trigonometric calculations

---

## Coordinate Systems

### Geographic (Lat/Lon)
- **Latitude**: -90 to +90 degrees (south to north)
- **Longitude**: -180 to +180 degrees (west to east)
- **Reference**: WGS84 ellipsoid

### Local Cartesian (North/East)
- **Origin**: Reference point (usually first position of each aircraft)
- **North**: Positive direction
- **East**: Positive direction
- **Units**: Meters
- **Conversion**: Varies by latitude (1 degree latitude = ~111km)

### Conversion Formulas

```python
# Earth radius
EARTH_RADIUS = 6371000.0  # meters

# Meters per degree (latitude - constant)
meters_per_deg_lat = math.pi * EARTH_RADIUS / 180.0

# Meters per degree (longitude - varies by latitude)
meters_per_deg_lon = meters_per_deg_lat * abs(math.cos(math.radians(latitude)))

# Convert delta meters to delta degrees
delta_lat = delta_north_meters / meters_per_deg_lat
delta_lon = delta_east_meters / meters_per_deg_lon

# Convert delta degrees to delta meters
delta_north_meters = delta_lat * meters_per_deg_lat
delta_east_meters = delta_lon * meters_per_deg_lon
```
