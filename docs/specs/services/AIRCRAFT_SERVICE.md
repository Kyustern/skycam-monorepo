# Aircraft Service Specification

## Overview

The `AircraftService` is responsible for fetching aircraft data from the OpenSky Network API. It provides a Python interface to query aircraft positions, velocities, and other flight information for a specified geographic area.

## Responsibilities

- Authenticate with OpenSky Network API using OAuth2 client credentials
- Fetch aircraft states for a bounding box or circular area
- Parse and structure raw API responses
- Cache access tokens to minimize authentication requests
- Maintain last known position for continuous tracking

## API Dependencies

- **OpenSky Network API**: Primary data source
  - Authentication endpoint: `https://auth.opensky-network.org/auth/realms/opensky-network/protocol/openid-connect/token`
  - States endpoint: `https://opensky-network.org/api/states/all`

## Configuration

### Secrets File (`secrets.json`)

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

### Default Location

The service uses the `DEFAULT_LOCATION` from secrets to:
- Define a default bounding box (1.5 degrees x 1.5 degrees centered on the location)
- Initialize the `last_position` tracking
- Fall back to when no position is specified in API calls

### Bounding Box Calculation

```
Center: (DEFAULT_LOCATION.latitude, DEFAULT_LOCATION.longitude)
Half range: 0.75 degrees (1.5 / 2)

lat_min = center_lat - 0.75
lat_max = center_lat + 0.75
lon_min = center_lon - 0.75
lon_max = center_lon + 0.75
```

## Class: AircraftService

### Methods

#### `__init__()`

Initialize the service and load secrets.

**Behavior:**
- Loads `clientId` and `clientSecret` from `secrets.json`
- Initializes token cache
- Computes default bounding box from `DEFAULT_LOCATION`
- Sets `last_position` to default location with 100km radius

**Raises:**
- `FileNotFoundError`: If `secrets.json` not found
- `ValueError`: If required credentials are missing

---

#### `_load_secrets() -> Dict[str, Any]`

Load secrets from `secrets.json` file.

**Search Paths:**
1. `./secrets.json` (relative to current working directory)
2. `../secrets.json` (relative to module directory)

**Returns:** Dictionary containing all secrets

**Raises:** `FileNotFoundError` if file not found at either path

---

#### `_get_client_credentials() -> tuple`

Retrieve OpenSky client credentials.

**Returns:** Tuple of `(client_id, client_secret)`

**Raises:** `ValueError` if credentials are missing

---

#### `_get_access_token() -> str`

Get or fetch a valid OAuth2 access token.

**Token Cache:**
- Tokens are cached with 30-minute expiry
- Automatic refresh when token expires

**Behavior:**
1. Check if cached token exists and is still valid
2. If valid, return cached token
3. If expired or not cached, fetch new token
4. Update cache with new token and timestamp
5. Return access token

**Returns:** Valid access token string

**Raises:**
- `ValueError`: If token cannot be obtained
- `requests.exceptions.RequestException`: If authentication fails

---

#### `get_aircraft_in_area(lat_min, lat_max, lon_min, lon_max) -> Dict[str, Any]`

Fetch aircraft data for a bounding box.

**Parameters:**
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| lat_min | float | No | Self.DEFAULT_LAT_MIN | Minimum latitude |
| lat_max | float | No | Self.DEFAULT_LAT_MAX | Maximum latitude |
| lon_min | float | No | Self.DEFAULT_LON_MIN | Minimum longitude |
| lon_max | float | No | Self.DEFAULT_LON_MAX | Maximum longitude |

**API Request:**
```
GET https://opensky-network.org/api/states/all
Headers: Authorization: Bearer <access_token>
Params:
  lamin=<lat_min>
  lamax=<lat_max>
  lomin=<lon_min>
  lomax=<lon_max>
```

**Returns:** Raw JSON response from OpenSky API

**Raises:** `requests.exceptions.RequestException` on HTTP errors

---

#### `get_aircraft_at_position(latitude, longitude, radius_km) -> Dict[str, Any]`

Fetch aircraft data around a circular position.

**Note:** OpenSky API doesn't support circular search directly, so this method approximates using a bounding box.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| latitude | float | Yes | Center latitude |
| longitude | float | Yes | Center longitude |
| radius_km | float | Yes | Search radius in kilometers |

**Behavior:**
1. Validates all parameters are present
2. Converts radius to degree deltas:
   - Latitude: `radius_km / 111.0` (1 degree ~ 111 km)
   - Longitude: `radius_km / (111.0 * abs(cos(latitude_radians)))`
3. Calculates bounding box
4. Updates `last_position` with current search parameters
5. Calls `get_aircraft_in_area()` with computed bounds

**Returns:** Raw JSON response from OpenSky API

**Raises:**
- `ValueError`: If required parameters are missing
- `requests.exceptions.RequestException`: On HTTP errors

---

#### `get_aircraft_at_last_pos(radius_km) -> Dict[str, Any]`

Fetch aircraft data around the last queried position.

**Parameters:**
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| radius_km | float | No | last_position["radius_km"] | Search radius override |

**Behavior:**
1. Uses `last_position` to get center coordinates
2. Uses provided `radius_km` or falls back to stored value
3. Calls `get_aircraft_at_position()` with cached/stored parameters

**Returns:** Raw JSON response from OpenSky API

---

## Data Structures

### OpenSky API Response Format

The OpenSky API returns aircraft states as a list of lists:

```python
{
    "time": 1234567890,
    "states": [
        [
            "icao24",           # 0: Unique ICAO 24-bit address
            "callsign",        # 1: Callsign (flight number)
            "origin_country",   # 2: Country of origin
            1234567890,        # 3: Unix timestamp (seconds) of position report
            1234567890,        # 4: Unix timestamp (seconds) of last contact
            2.781306,          # 5: Longitude (decimal degrees)
            41.678276,         # 6: Latitude (decimal degrees)
            1500.0,            # 7: Barometric altitude (meters)
            False,             # 8: On ground (boolean)
            250.0,             # 9: Velocity (m/s)
            45.0,              # 10: True track (degrees from north)
            0.0,               # 11: Vertical rate (m/s, positive = climbing)
            null,              # 12: Number of position reports
            1500.0,            # 13: Geometric altitude (meters)
            null,              # 14: Squawk code
            null,              # 15: SPI (Special Purpose Indicator)
            null               # 16: Position source
        ]
    ]
}
```

### State Keys

The service uses the following key mapping for parsed data:

```python
STATE_KEYS = [
    "icao", "callsign", "origin_country", "time_position", "last_contact",
    "longitude", "latitude", "baro_altitude", "on_ground", "velocity",
    "true_track", "vertical_rate", "sensors", "geo_altitude", "squawk",
    "spi", "position_source"
]
```

## Usage Examples

### Basic Usage

```python
from services.aircraft_service import aircraft_service

# Get aircraft in default area
_DATA = aircraft_service.get_aircraft_at_last_pos()
print(f"Found {len(data.get('states', []))} aircraft")

# Get aircraft at specific position
_DATA = aircraft_service.get_aircraft_at_position(
    latitude=41.678276,
    longitude=2.781306,
    radius_km=50.0
)

# Get aircraft in custom bounding box
_DATA = aircraft_service.get_aircraft_in_area(
    lat_min=41.5,
    lat_max=42.0,
    lon_min=2.5,
    lon_max=3.0
)
```

### Parsing Response

```python
from services.aircraft_service import aircraft_service

_DATA = aircraft_service.get_aircraft_at_last_pos()
STATE_KEYS = [
    "icao", "callsign", "origin_country", "time_position", "last_contact",
    "longitude", "latitude", "baro_altitude", "on_ground", "velocity",
    "true_track", "vertical_rate", "sensors", "geo_altitude", "squawk",
    "spi", "position_source"
]

for state in data.get('states', []):
    flight = dict(zip(STATE_KEYS, state))
    print(f"{flight['callsign']}: {flight['latitude']}, {flight['longitude']}")
```

---

## Error Handling

The service handles errors in the following ways:

1. **Missing Secrets**: Raises `FileNotFoundError` on startup
2. **Invalid Credentials**: Raises `ValueError` on authentication
3. **API Failures**: Raises `requests.exceptions.RequestException`
4. **Invalid Parameters**: Raises `ValueError` for missing required parameters

---

## Performance Considerations

- **Token Caching**: Access tokens are cached for 30 minutes
- **HTTP Requests**: Each API call makes a single HTTP request
- **Rate Limits**: OpenSky API has rate limits (not enforced by this service)
- **Concurrency**: The service is not thread-safe by default

---

## Testing

### Manual Testing

```python
# Test authentication
token = aircraft_service._get_access_token()
print(f"Token: {token[:20]}...")

# Test data fetching
data = aircraft_service.get_aircraft_at_last_pos()
print(f"States: {len(data.get('states', []))}")

# Test position tracking
print(f"Last position: {aircraft_service.last_position}")
```

### Expected Output

```python
# Successful response
{
    "time": 1724000000,
    "states": [
        ["404a3d", "ABC123", "France", 1724000000, 1724000000, 
         2.781306, 41.678276, 1500.0, False, 250.0, 45.0, 0.0, 
         null, 1500.0, null, null, null, null]
    ]
}

# Error: Missing parameters
ValueError: get_aircraft_at_position: Missing parameters
```

---

## Dependencies

### Python Packages
- `requests`: HTTP requests to OpenSky API
- `json`: JSON parsing
- `time`: Token caching and timestamps

### Files
- `secrets.json`: OpenSky credentials and default location

---

## Integration Points

The `AircraftService` is used by:
- `KalmanFilterService`: To get fresh aircraft data for tracking
- `app.py`: API endpoints for aircraft queries

It emits data that is:
- Streamed to frontend via WebSocket
- Used for Kalman filter updates
- Stored in capture files (via DataCaptureService)
