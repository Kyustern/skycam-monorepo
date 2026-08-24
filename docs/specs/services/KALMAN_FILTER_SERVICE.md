# Kalman Filter Service Specification

## Overview

The `KalmanFilterService` provides continuous position tracking and prediction for aircraft using Kalman filtering. It fills the gaps between OpenSky API updates (every 10 seconds) with smooth, predicted positions (every 500ms), enabling the turret to track aircraft continuously.

## Responsibilities

- Maintain Kalman filter tracks for multiple aircraft simultaneously
- Fetch aircraft data from `AircraftService` periodically
- Update filter states with new measurements
- Generate position predictions at regular intervals
- Stream predictions to frontend via WebSocket
- Handle aircraft appearance/disappearance (track initialization and cleanup)
- Provide statistics and status information

## Architecture

### Design Patterns

- **Thread-based concurrency**: Separate threads for data updates and predictions
- **Observer pattern**: WebSocket streaming of prediction updates
- **Factory pattern**: Automatic track creation for new aircraft
- **Singleton pattern**: Global service instance (`kalman_filter_service`)

### Coordinate Systems

The service uses multiple coordinate systems internally:

1. **Geographic (lat/lon)**: External API and output
2. **Local Cartesian (north/east)**: Internal filter state (meters relative to reference point)
3. **Velocity components**: North and east velocity components (m/s)

### Reference Points

Each aircraft track uses its initial position as a reference point:
- All position calculations are relative to this point
- Converted to geographic coordinates for output
- Reduces numerical errors for local tracking

## Configuration

### Timing Parameters

```python
# Update intervals
DATA_UPDATE_INTERVAL = 10.0      # Seconds between API fetches
PREDICTION_INTERVAL = 0.5       # Seconds between predictions

# Track management
MAX_MEASUREMENT_AGE = 60.0      # Seconds before track is marked as lost
```

### Tuning Parameters

```python
# Process noise (tunes filter responsiveness)
POSITION_PROCESS_NOISE = 10.0    # meters^2/s^3
VELOCITY_PROCESS_NOISE = 1.0     # (m/s)^2/s

# Measurement noise (tunes trust in OpenSky data)
POSITION_MEASUREMENT_NOISE = 100.0  # meters^2
```

### Earth Constants

```python
EARTH_RADIUS = 6371000.0  # meters
```

## Data Structures

### KalmanFilterState (Enum)

Track state enumeration:
- `INITIALIZING`: Track created but no measurements yet
- `TRACKING`: Track is actively being updated with measurements
- `LOST`: Track has not been updated within `MAX_MEASUREMENT_AGE`

### FlightPrediction (Dataclass)

Represents a predicted aircraft state at a given time:

```python
@dataclass
class FlightPrediction:
    callsign: str              # Flight identifier
    latitude: float            # Predicted latitude (degrees)
    longitude: float           # Predicted longitude (degrees)
    baro_altitude: float       # Barometric altitude (meters)
    velocity: float            # Speed (m/s)
    true_track: float          # Heading (degrees from north)
    vertical_rate: float       # Climb/descent rate (m/s)
    timestamp: float           # Unix timestamp of prediction
    covariance_lat: float      # Position uncertainty (degrees^2)
    covariance_lon: float      # Position uncertainty (degrees^2)
    covariance_alt: float      # Altitude uncertainty (meters^2)
    state: KalmanFilterState   # Current track state
    icao: str = ""             # ICAO 24-bit address
    origin_country: str = ""   # Country of origin
    on_ground: bool = False    # Whether aircraft is on ground
```

### FlightTrack (Dataclass)

Internal track state for Kalman filtering:

```python
@dataclass
class FlightTrack:
    callsign: str
    icao: str
    origin_country: str
    state_vector: np.ndarray       # [north, east, alt, v_north, v_east, v_alt]
    covariance_matrix: np.ndarray  # 6x6 covariance matrix
    ref_latitude: float           # Reference latitude (degrees)
    ref_longitude: float          # Reference longitude (degrees)
    last_measurement_time: float  # Timestamp of last measurement
    filter_state: KalmanFilterState
    Q: np.ndarray                 # Process noise covariance (6x6)
    R: np.ndarray                 # Measurement noise covariance (3x3)
    last_prediction_time: float  # Timestamp of last prediction
    predictions: List[FlightPrediction]  # Prediction history
```

## Class: KalmanFilterService

### State Variables

```python
_tracks: Dict[str, FlightTrack]            # callsign -> FlightTrack
_latest_predictions: Dict[str, FlightPrediction]  # Latest predictions
_latest_flight_data: Dict[str, Dict]      # Latest raw OpenSky data
_shutdown_flag: threading.Event          # Thread shutdown signal
_lock: threading.Lock                    # Thread synchronization
_data_update_thread: threading.Thread   # Background data update thread
_prediction_thread: threading.Thread    # Background prediction thread
_last_data_update: float                # Timestamp of last data update
_last_prediction: float                 # Timestamp of last prediction
_total_predictions: int                 # Counter for statistics
_total_measurements: int                 # Counter for statistics
```

### Methods

#### `__init__(aircraft_service_ref=None)`

Initialize the Kalman filter service.

**Parameters:**
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| aircraft_service_ref | AircraftService | No | Global `aircraft_service` | Reference to AircraftService |

**Behavior:**
- Initializes all state variables
- Sets up thread control structures
- Creates logger instance

---

#### `start()`

Start the background threads for data updates and predictions.

**Behavior:**
1. Checks if already running (prevents duplicate starts)
2. Clears shutdown flag
3. Creates and starts data update thread
4. Creates and starts prediction thread
5. Both threads run as daemon threads

**Thread Names:**
- `kalman-data-update`: Fetches data from AircraftService
- `kalman-prediction`: Generates predictions

---

#### `stop()`

Stop the background threads gracefully.

**Behavior:**
1. Sets shutdown flag
2. Waits for data update thread to finish (with timeout)
3. Waits for prediction thread to finish (with timeout)
4. Resets thread references
5. Logs shutdown completion

---

#### `is_running() -> bool`

Check if both threads are currently running.

**Returns:** `True` if both data and prediction threads are alive

---

#### `update_from_aircraft_service() -> Dict[str, Dict]`

Fetch new aircraft data and update all tracks.

**Behavior:**
1. Fetches data from `AircraftService.get_aircraft_at_last_pos()`
2. Parses OpenSky response into flight dictionary
3. Stores latest flight data in `_latest_flight_data`
4. Emits `aircraft_data` event via WebSocket
5. Initializes new tracks for new flights
6. Updates existing tracks with new measurements
7. Removes lost tracks (not updated for too long)
8. Returns parsed flight data

**Returns:** Dictionary of callsign -> flight data

**Emits:** `aircraft_data` WebSocket event

---

#### `_data_update_loop()`

Background thread that periodically fetches new data.

**Behavior:**
1. Runs in loop while shutdown flag is not set
2. Calls `update_from_aircraft_service()`
3. Logs update count
4. Sleeps for remaining interval time
5. Wakes periodically to check shutdown flag

**Interval:** `DATA_UPDATE_INTERVAL` (10 seconds)

---

#### `_prediction_loop()`

Background thread that periodically generates predictions.

**Behavior:**
1. Runs in loop while shutdown flag is not set
2. Generates predictions for all tracks
3. Stores latest predictions in `_latest_predictions`
4. Emits `prediction_data` event via WebSocket
5. Updates statistics counters
6. Logs prediction count
7. Sleeps for remaining interval time

**Interval:** `PREDICTION_INTERVAL` (500ms)

**Emits:** `prediction_data` WebSocket event

---

#### `_generate_predictions(predict_time) -> Dict[str, FlightPrediction]`

Generate predictions for all active tracks at a specific time.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| predict_time | float | Yes | Unix timestamp to predict to |

**Behavior:**
1. Iterates through all active tracks
2. Calls `_predict_track()` for each track
3. Returns dictionary of predictions

**Returns:** Dictionary of callsign -> FlightPrediction

---

#### `_predict_track(track, predict_time) -> FlightPrediction`

Generate a prediction for a single track at a specific time.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| track | FlightTrack | Yes | The track to predict |
| predict_time | float | Yes | Unix timestamp to predict to |

**Behavior:**
1. Calculates time delta from last measurement
2. Constructs state transition matrix F (constant velocity model)
3. Predicts state vector: `x_pred = F @ x`
4. Predicts covariance: `P_pred = F @ P @ F^T + Q`
5. Extracts predicted position in local Cartesian coordinates
6. Converts to geographic coordinates (lat/lon)
7. Converts velocity components to speed and heading
8. Converts position covariance from meters to degrees
9. Returns FlightPrediction object

**Returns:** FlightPrediction with predicted state

**State Transition Matrix:**
```
F = [1 0 0 dt 0  0 ]  # north += v_north * dt
    [0 1 0 0  dt 0 ]  # east += v_east * dt
    [0 0 1 0  0  dt]  # alt += v_alt * dt
    [0 0 0 1  0  0 ]  # v_north unchanged
    [0 0 0 0  1  0 ]  # v_east unchanged
    [0 0 0 0  0  1 ]  # v_alt unchanged
```

---

#### `_update_track_with_measurement(track, flight_data) -> bool`

Update a track with new measurement data using Kalman filter update step.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| track | FlightTrack | Yes | The track to update |
| flight_data | Dict | Yes | New measurement data |

**Behavior:**
1. Calculates time delta from last measurement
2. Extracts measurement position (lat/lon/alt)
3. Converts to local Cartesian coordinates relative to track reference
4. Predicts state to current time
5. Constructs measurement matrix H
6. Calculates measurement residual (innovation)
7. Calculates innovation covariance S
8. Calculates Kalman gain K
9. Updates state vector: `x = x_pred + K @ y`
10. Updates covariance matrix: `P = (I - K @ H) @ P_pred`
11. Updates last measurement time
12. Transitions filter state from INITIALIZING to TRACKING

**Returns:** `True` if update was successful

**Measurement Matrix:**
```
H = [1 0 0 0 0 0]  # north
    [0 1 0 0 0 0]  # east
    [0 0 1 0 0 0]  # altitude
```

---

#### `_initialize_new_tracks(flights) -> int`

Create Kalman filter tracks for newly detected aircraft.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| flights | Dict[str, Dict] | Yes | Dictionary of callsign -> flight data |

**Behavior:**
1. Iterates through all flights
2. Creates new FlightTrack for each unknown callsign
3. Skips ground vehicles (on_ground=True)
4. Initializes track state using `_create_flight_track()`

**Returns:** Number of new tracks created

---

#### `_create_flight_track(flight_data) -> FlightTrack`

Create a new FlightTrack for a detected aircraft.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| flight_data | Dict | Yes | Raw flight data from OpenSky API |

**Behavior:**
1. Extracts callsign, ICAO, origin_country
2. Sets initial position as reference point
3. Converts velocity and heading to north/east components
4. Initializes state vector: `[0, 0, alt, v_north, v_east, v_alt]`
5. Initializes covariance matrix with high uncertainty
6. Initializes process noise Q
7. Initializes measurement noise R

**Initial State Uncertainty:**
- Position: 1000 m^2 (std dev ~31.6m)
- Altitude: 1000 m^2 (std dev ~31.6m)
- Velocity: 100 (m/s)^2 (std dev ~10 m/s)
- Vertical velocity: 100 (m/s)^2

**Returns:** Initialized FlightTrack

---

#### `_remove_lost_tracks() -> int`

Remove tracks that haven't been updated for too long.

**Behavior:**
1. Calculates age of each track
2. Identifies tracks older than `MAX_MEASUREMENT_AGE` (60s)
3. Removes identified tracks from `_tracks`
4. Removes corresponding predictions from `_latest_predictions`

**Returns:** Number of tracks removed

---

#### `get_latest_predictions() -> List[Dict]`

Get the latest predictions for all tracked flights.

**Returns:** List of prediction dictionaries with callsign included

**Note:** Thread-safe (uses lock)

---

#### `get_prediction_for_flight(callsign) -> Optional[Dict]`

Get the latest prediction for a specific flight.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| callsign | str | Yes | The flight callsign |

**Returns:** Prediction data as dictionary, or `None` if not found

**Note:** Thread-safe (uses lock)

---

#### `get_track_count() -> int`

Get the number of currently tracked flights.

**Returns:** Number of active tracks

**Note:** Thread-safe (uses lock)

---

#### `get_statistics() -> Dict`

Get service statistics and status.

**Returns:** Dictionary containing:
```python
{
    "track_count": int,
    "prediction_count": int,
    "total_predictions": int,
    "total_measurements": int,
    "last_data_update": float,
    "last_prediction": float,
    "data_update_interval": float,
    "prediction_interval": float,
    "time_since_last_update": float,
    "time_since_last_prediction": float,
    "data_thread_alive": bool,
    "prediction_thread_alive": bool
}
```

**Note:** Thread-safe (uses lock)

---

## Coordinate Transformations

### `_degrees_to_meters(lat, delta_lat, delta_lon) -> Tuple[float, float]`

Convert latitude/longitude deltas to meters.

**Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| lat | float | Reference latitude (degrees) |
| delta_lat | float | Latitude delta (degrees) |
| delta_lon | float | Longitude delta (degrees) |

**Returns:** Tuple of (delta_north, delta_east) in meters

**Formulas:**
```
meters_per_deg_lat = pi * EARTH_RADIUS / 180.0
meters_per_deg_lon = meters_per_deg_lat * abs(cos(lat_radians))
```

---

### `_meters_to_degrees(lat, delta_north, delta_east) -> Tuple[float, float]`

Convert meter deltas to latitude/longitude deltas.

**Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| lat | float | Reference latitude (degrees) |
| delta_north | float | North delta (meters) |
| delta_east | float | East delta (meters) |

**Returns:** Tuple of (delta_lat, delta_lon) in degrees

---

## Kalman Filter Implementation

### Constant Velocity Model

The service uses a **constant velocity motion model** for aircraft tracking:

- **State Vector**: `[north, east, alt, v_north, v_east, v_alt]`
  - Positions: meters relative to reference point
  - Velocities: meters per second
  - All 6 elements form the complete state

- **Process Model**: Constant velocity between measurements
  - Position changes by velocity × time
  - Velocity remains constant (no acceleration)

- **Measurement Model**: Direct position measurements
  - Measures north, east, and altitude
  - Does not directly measure velocities

### Noise Parameters

**Process Noise (Q):**
- Models uncertainty in the motion model
- Tunes how quickly the filter responds to changes
- Higher values = more responsive to changes
- Current: `POSITION_PROCESS_NOISE = 10.0`, `VELOCITY_PROCESS_NOISE = 1.0`

**Measurement Noise (R):**
- Models uncertainty in OpenSky data
- Tunes trust in measurements vs. predictions
- Higher values = more trust in predictions
- Current: `POSITION_MEASUREMENT_NOISE = 100.0` (10m std dev)

### Filter Cycle

1. **Predict Step**: Predict state forward in time
   - State: `x_pred = F @ x`
   - Covariance: `P_pred = F @ P @ F^T + Q`

2. **Update Step**: Incorporate new measurement
   - Innovation: `y = z - H @ x_pred`
   - Innovation covariance: `S = H @ P_pred @ H^T + R`
   - Kalman gain: `K = P_pred @ H^T @ S^-1`
   - State update: `x = x_pred + K @ y`
   - Covariance update: `P = (I - K @ H) @ P_pred`

## Usage Examples

### Starting the Service

```python
from services.kalman_filter_service import kalman_filter_service

# Start background threads
kalman_filter_service.start()

# Check if running
print(f"Running: {kalman_filter_service.is_running()}")
```

### Getting Predictions

```python
# Get all latest predictions
predictions = kalman_filter_service.get_latest_predictions()
print(f"Tracking {len(predictions)} aircraft")

# Get specific flight
prediction = kalman_filter_service.get_prediction_for_flight("ABC123")
if prediction:
    print(f"{prediction['callsign']} at {prediction['latitude']}, {prediction['longitude']}")
```

### Getting Statistics

```python
stats = kalman_filter_service.get_statistics()
print(f"Track count: {stats['track_count']}")
print(f"Total predictions: {stats['total_predictions']}")
print(f"Data thread alive: {stats['data_thread_alive']}")
```

### Stopping the Service

```python
kalman_filter_service.stop()
```

---

## WebSocket Integration

The service emits two WebSocket events:

1. **`aircraft_data`**: Emitted when new data is fetched from OpenSky
   - Contains: Raw flight data dictionary
   - Frequency: Every 10 seconds

2. **`prediction_data`**: Emitted when new predictions are generated
   - Contains: List of prediction dictionaries
   - Frequency: Every 500ms

**Connection Example:**
```javascript
const socket = io('http://localhost:5000', { path: '/api/ws' });

socket.on('aircraft_data', (data) => {
    console.log('New aircraft data:', Object.keys(data).length, 'flights');
});

socket.on('prediction_data', (predictions) => {
    console.log('New predictions:', predictions.length, 'flights');
    predictions.forEach(p => {
        console.log(`${p.callsign}: ${p.latitude}, ${p.longitude}`);
    });
});
```

---

## Tuning Guide

### Tuning Parameters

The Kalman filter has several tuning parameters that affect its behavior:

1. **`POSITION_PROCESS_NOISE`** (default: 10.0)
   - Controls expected position drift between measurements
   - Increase if aircraft maneuver frequently
   - Decrease for more stable, straight-line flights

2. **`VELOCITY_PROCESS_NOISE`** (default: 1.0)
   - Controls expected velocity changes
   - Increase for more agile aircraft
   - Decrease for more predictable movements

3. **`POSITION_MEASUREMENT_NOISE`** (default: 100.0)
   - Controls trust in OpenSky measurements
   - Increase if OpenSky data is noisy
   - Decrease if OpenSky data is highly accurate

4. **`DATA_UPDATE_INTERVAL`** (default: 10.0s)
   - Time between OpenSky API calls
   - Shorter = more frequent updates but higher API usage
   - Longer = less API usage but less accurate tracking

5. **`PREDICTION_INTERVAL`** (default: 0.5s)
   - Time between prediction generations
   - Shorter = smoother turret movement
   - Longer = less CPU usage

6. **`MAX_MEASUREMENT_AGE`** (default: 60.0s)
   - Time before a track is considered lost
   - Increase to keep tracks longer
   - Decrease to clean up stale tracks faster

### Initial State Uncertainty

The initial covariance matrix values can also be tuned:

```python
# Current values
position_var = 1000.0      # 31.6m std dev
velocity_var = 100.0       # 10 m/s std dev
altitude_var = 1000.0
vertical_velocity_var = 100.0

# For more precise initial estimates (if you have good first measurement)
position_var = 100.0       # 10m std dev
velocity_var = 25.0        # 5 m/s std dev

# For more uncertain initial estimates
position_var = 10000.0     # 100m std dev
velocity_var = 400.0       # 20 m/s std dev
```

### Tuning Procedure

1. **Start with defaults** and observe behavior
2. **Check covariance values** in predictions to understand uncertainty
3. **Increase process noise** if predictions lag behind actual positions
4. **Decrease measurement noise** if predictions are too noisy
5. **Adjust update intervals** based on network conditions and API limits
6. **Monitor `get_statistics()`** to verify thread health

---

## Error Handling

The service handles errors gracefully:

- **Thread errors**: Caught and logged, thread continues running
- **Singular matrices**: Handled in Kalman gain calculation
- **Invalid data**: Skipped with error logging
- **Missing tracks**: Returns empty results rather than errors

---

## Performance Considerations

- **Thread Safety**: All shared state access is protected by locks
- **Memory Usage**: Tracks store prediction history (can grow over time)
- **CPU Usage**: Prediction loop runs every 500ms for all active tracks
- **Network**: Data update loop makes HTTP requests every 10 seconds

---

## Dependencies

### Python Packages
- `numpy`: Matrix operations and numerical computing
- `threading`: Background thread management
- `time`: Timing and timestamps
- `math`: Trigonometric functions

### Internal Dependencies
- `services.aircraft_service`: Data source
- `socketio_instance`: WebSocket communication
- `utils.logger`: Logging utilities

---

## Integration Points

The `KalmanFilterService` is used by:
- `app.py`: API endpoints for predictions and statistics
- `DataCaptureService` (new): Source of prediction data for logging
- Frontend: WebSocket streaming of predictions
- Turret control: Position data for aiming calculations
