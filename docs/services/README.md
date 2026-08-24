# Services Documentation

This directory contains detailed specifications for all Turret system services.

## Service Overview

| Service | File | Purpose | Status |
|---------|------|---------|--------|
| [Aircraft Service](../specs/services/AIRCRAFT_SERVICE.md) | `services/aircraft_service.py` | Fetch aircraft data from OpenSky API | Implemented |
| [Kalman Filter Service](../specs/services/KALMAN_FILTER_SERVICE.md) | `services/kalman_filter_service.py` | Track and predict aircraft positions | Implemented |
| [Data Capture Service](../specs/services/DATA_CAPTURE_SERVICE.md) | `services/data_capture_service.py` | Log data for Jupyter analysis | **NEW - To Implement** |

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Turret Server                            │
├─────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────┐    ┌──────────────────┐    ┌────────┐ │
│  │                  │    │                  │    │        │ │
│  │  AircraftService  │────▶│ KalmanFilterSvc │────▶│  App   │ │
│  │                  │    │                  │    │        │ │
│  └──────────────────┘    └────────┬─────────┘    └────────┘ │
│                                       │                      │
│                                       ▼                      │
│                              ┌──────────────────┐             │
│                              │                  │             │
│                              │  DataCaptureSvc  │             │
│                              │                  │             │
│                              └────────┬─────────┘             │
│                                       │                      │
│                                       ▼                      │
│                            ┌──────────────────┐              │
│                            │                  │              │
│                            │  captures/        │              │
│                            │  *.h5 files       │              │
│                            │                  │              │
│                            └──────────────────┘              │
│                                                                  │
└─────────────────────────────────────────────────────────────┘
```

## Data Flow

1. **AircraftService** fetches raw data from OpenSky Network API
2. **KalmanFilterService** processes and tracks aircraft, generating predictions
3. **DataCaptureService** logs all data for analysis
4. **App** serves data to frontend via REST and WebSocket

## Service Interdependencies

- `AircraftService` → `KalmanFilterService`: Provides raw aircraft data
- `KalmanFilterService` → `DataCaptureService`: Provides predictions and statistics
- `AircraftService` → `DataCaptureService`: Provides raw OpenSky data

## Implementation Status

### Existing Services
- ✅ **AircraftService**: Complete, functional
- ✅ **KalmanFilterService**: Complete, functional with tuning parameters

### New Service (This PR)
- 📋 **DataCaptureService**: Specification complete, ready for implementation

## Next Steps

To implement the DataCaptureService:

1. Create `server/services/data_capture_service.py` with the class definition
2. Add `h5py` to `server/requirements.txt`
3. Add API endpoints to `server/app.py`
4. Update `server/services/__init__.py` to export the new service
5. Add logger instance to `server/utils/logger.py`
6. Start/stop the service with the server

See [Data Capture Service Specification](../specs/services/DATA_CAPTURE_SERVICE.md) for complete implementation details.
