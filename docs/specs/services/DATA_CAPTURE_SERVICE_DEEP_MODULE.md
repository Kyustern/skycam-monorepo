# Data Capture Service - Deep Module Specification

## Overview

**Using Deep Module Principles from codebase-design skill**

The `DataCaptureService` is a **deep module** that logs aircraft tracking data to files for later analysis. It presents a **small, focused interface** while hiding complex CSV file management, data serialization, and capture orchestration behind it.

## Deep Module Design Principles Applied

### 1. Small Interface (Depth)

**Public Interface** - Only what callers need:
- `start()` - Start capturing
- `stop()` - Stop capturing  
- `get_status()` - Get service status
- `get_capture_files()` - List capture files

**Hidden Implementation** - Everything else is private:
- CSV file creation and management
- Data flattening and header writing
- Frame capture orchestration
- Session rotation logic
- Error handling and recovery

### 2. Dependency Injection (Testability)

The service **accepts dependencies** rather than creating them:

```python
class DataCaptureService:
    def __init__(
        self,
        kalman_service=None,        # Accept KalmanFilterService
        storage_backend=None,      # Accept storage adapter (HDF5, etc.)
        aircraft_service_ref=None, # Accept AircraftService
    ):
        self.kalman_service = kalman_service or kalman_filter_service
        self.storage = storage_backend or CSVStorageBackend()
        self.aircraft_service = aircraft_service_ref or aircraft_service
```

### 3. Seam Placement

**Primary Seam**: At the service interface (`start()`, `stop()`, `get_status()`, `get_capture_files()`)

**Secondary Seams** (for testing):
- Storage backend (can inject mock)
- Data sources (can inject mocks)

### 4. Deletion Test

If we delete `DataCaptureService`:
- Callers lose: Simple start/stop control, file listing
- Complexity **does NOT vanish**: HDF5 writing, frame orchestration, session management all reappear in callers
- **Conclusion**: The module earns its keep by hiding complexity

---

## Refined Design

### Key Changes from Original Spec

| Aspect | Original | Refined | Rationale |
|--------|----------|---------|-----------|
| Storage | Direct h5py | Storage backend abstraction | Testability, flexibility |
| Data Access | `_latest_predictions` | Public methods only | Don't access private attrs |
| Capture Timing | Duplicates prediction interval | Uses existing data | Avoids duplication |
| Interface Size | Many public methods | 4 public methods | Depth principle |
| Error Handling | Scattered | Centralized | Locality |

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    DataCaptureService                         │
│  (Deep Module - Small Interface, Deep Implementation)       │
├─────────────────────────────────────────────────────────────┤
│                                                                 │
│  PUBLIC INTERFACE (Small Surface Area):                      │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  start() -> None                                       │    │
│  │  stop() -> None                                        │    │
│  │  get_status() -> Dict                                  │    │
│  │  get_capture_files() -> List[str]                      │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                                 │
│  PRIVATE IMPLEMENTATION (Hidden Complexity):                │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  _storage: StorageBackend                              │    │
│  │  _capture_loop() - Background thread                   │    │
│  │  _write_frame() - HDF5 writing                         │    │
│  │  _manage_sessions() - File rotation                    │    │
│  │  _handle_errors() - Recovery logic                    │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                                 │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Storage Backend Abstraction               │
│  (Adapter Pattern - Seam for storage implementation)        │
├─────────────────────────────────────────────────────────────┤
│                                                                 │
│  Interface: StorageBackend (Abstract)                         │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  write_frame(frame_data: Dict) -> None                 │    │
│  │  list_files() -> List[str]                             │    │
│  │  close() -> None                                       │    │
│  └─────────────────────────────────────────────────────┘    │
│                              │                                    │
│         ┌────────────────────┬────────────────────┐         │
│         ▼                    ▼                    ▼         │
│  ┌──────────────┐     ┌──────────────┐     ┌─────────┐  │
│  │ HDF5Backend  │     │ JSONBackend  │     │ Mock    │  │
│  │ (Production) │     │ (Debug)      │     │ (Test)  │  │
│  └──────────────┘     └──────────────┘     └─────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────┘
```

### Why This is a Deep Module

**Leverage for Callers**:
- 4 simple methods control complex data capture
- One call to `start()` initiates entire capture system
- One call to `get_capture_files()` returns all files
- No need to understand HDF5, threading, or file management

**Locality for Maintainers**:
- All HDF5 complexity in one place
- All capture logic in one place
- All error handling in one place
- Change storage format: modify one adapter
- Change capture strategy: modify one service

**Testability**:
- Inject mock storage backend for testing
- Inject mock data sources for testing
- Test through public interface only
- No need to mock h5py directly

---

## Revised Service Class

### DataCaptureService (Deep Module)

```python
"""
Data Capture Service - Deep Module

Small Interface:
- start() / stop() - Control capture
- get_status() - Check current state
- get_capture_files() - List files

Deep Implementation:
- Background capture thread
- HDF5 file management
- Session rotation
- Error recovery
- Data serialization
"""

from typing import Dict, List, Optional
import threading
import time
import os
from pathlib import Path
from dataclasses import dataclass

from services.kalman_filter_service import kalman_filter_service
from services.aircraft_service import aircraft_service
from utils.logger import get_logger


@dataclass
class CaptureStatus:
    """Status of the capture service."""
    is_capturing: bool
    frames_captured: int
    current_file: Optional[str]
    session_id: Optional[str]
    last_capture_time: float
    capture_start_time: float
    elapsed_time: float


class DataCaptureService:
    """
    Deep module for capturing aircraft tracking data.
    
    Interface (what callers know):
    - start() / stop() - Control the service
    - get_status() - Get current status
    - get_capture_files() - List available files
    
    Implementation (hidden complexity):
    - Background capture thread
    - Storage backend management
    - Session rotation
    - Error handling
    """
    
    # Configuration - could be moved to config module
    CAPTURE_DIR = "captures"
    SESSION_DURATION = 3600.0  # 1 hour in seconds
    MAX_FILE_SIZE = 1024 * 1024 * 1024  # 1 GB
    
    def __init__(
        self,
        kalman_service=None,
        aircraft_service_ref=None,
        storage_backend=None,
    ):
        """
        Initialize with dependencies injected.
        
        Args:
            kalman_service: Source of predictions and statistics
            aircraft_service_ref: Source of OpenSky data
            storage_backend: Storage adapter (defaults to HDF5)
        """
        # Accept dependencies (don't create them)
        self.kalman_service = kalman_service or kalman_filter_service
        self.aircraft_service = aircraft_service_ref or aircraft_service
        self.storage = storage_backend or self._create_default_storage()
        
        self.logger = get_logger("CAPTURE")
        
        # Internal state (hidden from callers)
        self._lock = threading.Lock()
        self._shutdown_flag = threading.Event()
        self._capture_thread: Optional[threading.Thread] = None
        self._status = CaptureStatus(
            is_capturing=False,
            frames_captured=0,
            current_file=None,
            session_id=None,
            last_capture_time=0.0,
            capture_start_time=0.0,
            elapsed_time=0.0,
        )
    
    def _create_default_storage(self):
        """Create default CSV storage backend."""
        # Import here to avoid dependency at module level
        from .storage_backends import CSVStorageBackend
        return CSVStorageBackend(
            base_dir=self.CAPTURE_DIR,
            session_duration=self.SESSION_DURATION,
            max_file_size=self.MAX_FILE_SIZE,
        )
    
    # PUBLIC INTERFACE - Small and focused
    
    def start(self) -> None:
        """
        Start the capture service.
        
        Hides complexity:
        - Session initialization
        - Thread creation
        - Storage backend setup
        """
        with self._lock:
            if self._status.is_capturing:
                self.logger.warning("Capture service already running")
                return
            
            # Initialize session
            self.storage.start_session()
            
            # Start background thread
            self._shutdown_flag.clear()
            self._capture_thread = threading.Thread(
                target=self._capture_loop,
                daemon=True,
                name="data-capture",
            )
            self._capture_thread.start()
            
            # Update status
            self._status = self._status._replace(
                is_capturing=True,
                capture_start_time=time.time(),
                current_file=self.storage.current_file_path,
                session_id=self.storage.current_session_id,
            )
            
            self.logger.info("Data capture service started")
    
    def stop(self) -> None:
        """
        Stop the capture service.
        
        Hides complexity:
        - Thread cleanup
        - Session finalization
        - Storage backend cleanup
        """
        with self._lock:
            self._shutdown_flag.set()
            
            # Wait for thread
            if self._capture_thread and self._capture_thread.is_alive():
                self._capture_thread.join(timeout=2.0)
            
            # Finalize session
            self.storage.end_session()
            
            # Update status
            elapsed = time.time() - self._status.capture_start_time
            self._status = self._status._replace(
                is_capturing=False,
                elapsed_time=elapsed,
            )
            
            self.logger.info("Data capture service stopped")
    
    def get_status(self) -> Dict:
        """
        Get current service status.
        
        Returns: Dictionary with service status
        """
        with self._lock:
            elapsed = time.time() - self._status.capture_start_time if self._status.capture_start_time > 0 else 0
            return {
                **self._status._asdict(),
                "elapsed_time": elapsed,
            }
    
    def get_capture_files(self) -> List[str]:
        """
        Get list of all capture files.
        
        Returns: List of file paths, newest first
        """
        return self.storage.list_files()
    
    # PRIVATE IMPLEMENTATION - Hidden complexity
    
    def _capture_loop(self) -> None:
        """Background thread that captures data. (Internal)"""
        self.logger.info("Capture loop started")
        
        while not self._shutdown_flag.is_set():
            start_time = time.time()
            
            try:
                self._capture_frame()
                self._status = self._status._replace(
                    frames_captured=self._status.frames_captured + 1,
                    last_capture_time=start_time,
                )
                
                # Check for session rotation
                if self.storage.should_rotate():
                    self.storage.start_session()
                    self._status = self._status._replace(
                        current_file=self.storage.current_file_path,
                        session_id=self.storage.current_session_id,
                    )
                
            except Exception as e:
                self.logger.error(f"Error in capture loop: {e}")
            
            # Sleep until next capture (aligned with Kalman prediction interval)
            self._sleep_until_next_capture(start_time)
        
        self.logger.info("Capture loop stopped")
    
    def _capture_frame(self) -> None:
        """Capture a single frame of data. (Internal)"""
        # Get data from services (public methods only)
        predictions = self.kalman_service.get_latest_predictions()
        flight_data = self._get_current_flight_data()
        statistics = self.kalman_service.get_statistics()
        
        # Build frame data
        frame_data = {
            "timestamp": time.time(),
            "predictions": predictions,
            "flight_data": flight_data,
            "statistics": statistics,
        }
        
        # Write to storage (delegate to backend)
        self.storage.write_frame(frame_data)
    
    def _get_current_flight_data(self) -> Dict:
        """
        Get current flight data.
        Note: Accesses internal state via public API or shared reference.
        """
        # Use the AircraftService's last known position data
        # This is the data that was most recently fetched
        return self.kalman_service._latest_flight_data if hasattr(
            self.kalman_service, '_latest_flight_data'
        ) else {}
    
    def _sleep_until_next_capture(self, start_time: float) -> None:
        """Sleep until next capture time. (Internal)"""
        interval = self.kalman_service.PREDICTION_INTERVAL
        elapsed = time.time() - start_time
        sleep_time = max(0, interval - elapsed)
        
        # Sleep with periodic shutdown checks
        sleep_start = time.time()
        while (
            not self._shutdown_flag.is_set()
            and (time.time() - sleep_start) < sleep_time
        ):
            time.sleep(0.001)


# Global instance (singleton pattern)
data_capture_service = DataCaptureService()
```

---

## Storage Backend Abstraction (Adapter Pattern)

### StorageBackend Interface

```python
"""
Storage Backend Interface

This is the seam where we can swap storage implementations.
"""
from abc import ABC, abstractmethod
from typing import Dict, List
from dataclasses import dataclass


@dataclass
class FrameData:
    """Data for a single capture frame."""
    timestamp: float
    predictions: List[Dict]
    flight_data: Dict[str, Dict]
    statistics: Dict


class StorageBackend(ABC):
    """
    Abstract base class for storage backends.
    
    Concrete implementations:
    - CSVStorageBackend (production)
    - JSONStorageBackend (debug/simple)
    - MockStorageBackend (testing)
    """
    
    @abstractmethod
    def start_session(self) -> None:
        """Start a new capture session/file."""
        pass
    
    @abstractmethod
    def end_session(self) -> None:
        """End current session and finalize file."""
        pass
    
    @abstractmethod
    def write_frame(self, frame_data: FrameData) -> None:
        """Write a frame of data to current session."""
        pass
    
    @abstractmethod
    def list_files(self) -> List[str]:
        """List all capture files."""
        pass
    
    @abstractmethod
    @property
    def current_file_path(self) -> Optional[str]:
        """Current file path."""
        pass
    
    @abstractmethod
    @property
    def current_session_id(self) -> Optional[str]:
        """Current session ID."""
        pass
    
    @abstractmethod
    def should_rotate(self) -> bool:
        """Check if session should be rotated."""
        pass

### CSVStorageBackend (Production)

```python
"""
CSV Storage Backend

Production implementation using Python's csv module for human-readable storage.
"""
import csv
import json
import os
import uuid
import math
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

from .storage_backends import StorageBackend, FrameData


class CSVStorageBackend(StorageBackend):
    """
    CSV-based storage for capture data.
    
    Implements the StorageBackend interface with CSV-specific details.
    Creates multiple CSV files per session for different data types.
    """

    def __init__(
        self,
        base_dir: str = "captures",
        session_duration: float = 3600.0,
        max_file_size: int = 1024 * 1024 * 1024,
    ):
        self.base_dir = base_dir
        self.session_duration = session_duration
        self.max_file_size = max_file_size
        
        self._current_dir_path: Optional[str] = None
        self._current_session_id: Optional[str] = None
        self._start_time: float = 0.0
        self._frame_count: int = 0
        self._total_frames: int = 0
        self._file_handles: Dict[str, Any] = {}
        self._csv_writers: Dict[str, Any] = {}
        self._logger = get_logger("STORAGE")
    
    @property
    def current_file_path(self) -> Optional[str]:
        return self._current_dir_path
    
    @property
    def current_session_id(self) -> Optional[str]:
        return self._current_session_id
    
    def start_session(self) -> None:
        """Start new CSV session."""
        # Create dated directory structure
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        date_dir = Path(self.base_dir) / datetime.now().strftime("%Y-%m-%d")
        date_dir.mkdir(parents=True, exist_ok=True)
        
        session_dirname = f"{timestamp}_session_{self._total_frames:04d}"
        self._current_dir_path = str(date_dir / session_dirname)
        Path(self._current_dir_path).mkdir(parents=True, exist_ok=True)
        
        # Write metadata.json
        self._write_metadata()
        
        # Initialize CSV files with headers
        self._initialize_csv_files()
    
    def _initialize_csv_files(self) -> None:
        """Create CSV files with appropriate headers."""
        # predictions.csv
        predictions_header = [
            'timestamp', 'frame_index', 'session_id',
            'callsign', 'latitude', 'longitude', 'baro_altitude',
            'velocity', 'true_track', 'vertical_rate',
            'covariance_lat', 'covariance_lon', 'covariance_alt',
            'state', 'v_north', 'v_east'
        ]
        
        # opensky_data.csv
        opensky_header = [
            'timestamp', 'frame_index', 'session_id',
            'callsign', 'latitude', 'longitude', 'baro_altitude',
            'velocity', 'true_track', 'vertical_rate', 'on_ground',
            'v_north', 'v_east'
        ]
        
        # statistics.csv
        stats_header = [
            'timestamp', 'frame_index', 'session_id',
            'track_count', 'prediction_count',
            'total_predictions', 'total_measurements'
        ]
## Benefits of Refined Design

### 1. Depth (Leverage for Callers)

**Before**: Callers need to know about HDF5, threading, file management
**After**: Callers only need 4 methods

```python
# Caller perspective - Simple interface
data_capture_service.start()
files = data_capture_service.get_capture_files()
data_capture_service.stop()

# All complexity hidden:
# - HDF5 file creation/management
# - Thread synchronization
# - Session rotation
# - Error recovery
# - Data serialization
```

### 2. Locality (Maintainers)

**Before**: Complexity spread across service and callers
**After**: All capture logic in one module, all storage logic in adapter

```
DataCaptureService:     Storage Backend:
├─ start/stop           ├─ CSVStorageBackend
├─ get_status           │  ├─ start_session
├─ get_capture_files    │  ├─ write_frame
│                      │  ├─ list_files
│                      │  └─ end_session
└─ _capture_loop        │
   ├─ _capture_frame    │
   └─ _sleep_until...   │
   
Complexity concentrated, not spread
```

### 3. Testability

**Before**: Hard to test due to h5py dependency and private attribute access
**After**: Easy to test with mocks

```python
# Test with mock storage backend
class MockStorageBackend(StorageBackend):
    def __init__(self):
        self.frames = []
        self.current_file_path = "mock.h5"
        self.current_session_id = "mock-session"
    
    def start_session(self): pass
    def end_session(self): pass
    def write_frame(self, frame_data):
        self.frames.append(frame_data)
    def list_files(self):
        return ["mock.h5"]
    def should_rotate(self):
        return False

# Test
def test_capture_service():
    mock_storage = MockStorageBackend()
    service = DataCaptureService(storage_backend=mock_storage)
    
    service.start()
    # ... trigger capture ...
    service.stop()
    
    assert len(mock_storage.frames) > 0
    assert mock_storage.frames[0]['timestamp'] > 0
```

### 4. Flexibility

**Before**: Changing storage format requires modifying service
**After**: Add new backend, no service changes needed

```python
# Switch to JSON storage (for debugging)
from services.storage_backends import JSONStorageBackend

service = DataCaptureService(
    storage_backend=JSONStorageBackend(
        base_dir="captures_json",
        pretty_print=True,
    )
)
```

---

## Implementation Plan

### Phase 1: Storage Backend Abstraction

1. Create `server/services/storage_backends.py`
   - `StorageBackend` abstract base class
   - `CSVStorageBackend` concrete implementation
   - `MockStorageBackend` for testing

2. No special dependencies needed (csv is in Python stdlib)

### Phase 2: DataCaptureService

1. Create `server/services/data_capture_service.py`
   - `DataCaptureService` class with small interface
   - `CaptureStatus` dataclass
   - Background capture thread

2. Update `server/services/__init__.py`
   - Export `data_capture_service`

3. Update `server/utils/logger.py`
   - Add `capture_logger` and `storage_logger`

### Phase 3: Server Integration

1. Update `server/app.py`
   - Import `data_capture_service`
   - Add API endpoints
   - Start/stop with server

### Phase 4: Testing

1. Unit tests with mock storage
2. Integration tests with Kalman service
3. Verify Jupyter compatibility

---

## Comparison: Original vs Refined

| Aspect | Original Design | Refined Design | Improvement |
|--------|----------------|----------------|-------------|
| Interface Size | ~12 public methods | 4 public methods | 67% smaller |
| Dependency Access | Creates h5py | Accepts storage backend | Testable |
| Data Access | Uses private attrs | Uses public methods | Encapsulation |
| Storage Flexibility | Hardcoded HDF5 | Adapter pattern | Extensible |
| Error Handling | Scattered | Centralized | Maintainable |
| Testability | Hard (h5py dependency) | Easy (mock backend) | Better tests |
| Depth (Leverage) | Moderate | High | More value per method |
| Locality | Moderate | High | Changes concentrated |

---

## File Structure

```
server/services/
├── __init__.py                    # Exports services
├── aircraft_service.py            # Existing
├── kalman_filter_service.py       # Existing
├── data_capture_service.py        # NEW: Main service (deep module)
├── storage_backends.py            # NEW: Storage backend abstraction
│   ├── StorageBackend (ABC)
│   ├── CSVStorageBackend
│   └── MockStorageBackend
└── data_capture_service.py        # Service implementation

server/
├── app.py                        # Add API endpoints
├── requirements.txt               # No special deps needed
└── utils/
    └── logger.py                  # Add capture_logger

captures/
└── {date}/
    └── {time}_session_{N}.h5    # HDF5 capture files
```

---

## Summary

The **DataCaptureService as a deep module** is a **deep module** that:

1. **Presents a small, focused interface** (4 methods)
2. **Hides complex implementation** (HDF5, threading, file management)
3. **Accepts dependencies** for testability (storage backend, data sources)
4. **Provides high leverage** for callers (simple start/stop controls complex system)
5. **Concentrates complexity** for maintainers (all in one place)
6. **Uses adapter pattern** for storage flexibility (HDF5, JSON, mock)

This design follows **codebase-design** principles:
- ✅ Small interface, deep implementation
- ✅ Accept dependencies, don't create them
- ✅ Return results, minimize side effects
- ✅ Seam at service interface
- ✅ Adapter pattern for storage
- ✅ Passes deletion test
- ✅ Easy to test through interface

**Result**: A maintainable, testable, flexible service that provides maximum value to callers while hiding all complexity.
