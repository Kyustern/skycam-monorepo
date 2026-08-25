"""
Storage Backend Abstraction for Data Capture Service

This module provides the StorageBackend interface and concrete implementations
following the Adapter pattern. This allows the DataCaptureService to be
agnostic about the storage format while providing flexibility and testability.

Design Principles:
- StorageBackend is the SEAM where storage implementations vary
- CSVStorageBackend is the production ADAPTER for CSV output
- MockStorageBackend is for testing
- Follows "accept dependencies, don't create them" principle

CSV Output Format:
- Each session creates multiple CSV files in a dated directory structure
- Main files: predictions.csv, opensky_data.csv, statistics.csv, metadata.json
- Predictions are flattened with one row per prediction entry
- OpenSky data is flattened with one row per aircraft per frame
- Statistics are written as time-series data
"""

import os
import json
import uuid
import time
import csv
from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Any
from pathlib import Path


@dataclass
class FrameData:
    """
    Data for a single capture frame.
    
    This is the data structure passed from DataCaptureService to StorageBackend.
    It contains all information needed to reconstruct a frame of aircraft tracking data.
    """
    timestamp: float              # Unix timestamp of capture
    predictions: List[Dict]        # List of prediction dicts (from KalmanFilterService)
    flight_data: Dict[str, Dict]  # OpenSky data (callsign -> flight data)
    statistics: Dict              # Kalman filter statistics


class StorageBackend(ABC):
    """
    Abstract Base Class for Storage Backends.
    
    This is the SEAM where storage implementations can vary.
    Concrete implementations satisfy this interface to provide different
    storage formats (CSV, HDF5, JSON, etc.)
    
    Design Principles:
    - Interface includes everything a storage backend must provide
    - Implementation details are hidden behind this interface
    - Callers (DataCaptureService) only depend on this abstract class
    """
    
    @property
    @abstractmethod
    def current_file_path(self) -> Optional[str]:
        """Get the current file path, or None if no active session."""
        pass
    
    @property
    @abstractmethod
    def current_session_id(self) -> Optional[str]:
        """Get the current session ID, or None if no active session."""
        pass
    
    @abstractmethod
    def start_session(self) -> None:
        """
        Start a new capture session/file.
        
        Creates new file, writes metadata, prepares for frame writes.
        """
        pass
    
    @abstractmethod
    def end_session(self) -> None:
        """
        End the current capture session.
        
        Finalizes the file, writes end metadata, closes resources.
        """
        pass
    
    @abstractmethod
    def write_frame(self, frame_data: FrameData) -> None:
        """
        Write a frame of data to the current session.
        
        Args:
            frame_data: The frame data to write
        """
        pass
    
    @abstractmethod
    def list_files(self) -> List[str]:
        """
        List all capture files.
        
        Returns:
            List of file paths, newest first
        """
        pass
    
    @abstractmethod
    def should_rotate(self) -> bool:
        """
        Check if the session should be rotated.
        
        Returns:
            True if session should rotate (time or size limit reached)
        """
        pass


class CSVStorageBackend(StorageBackend):
    """
    CSV-based Storage Backend for Production.
    
    This is the ADAPTER that implements StorageBackend interface using CSV files.
    It provides human-readable, widely-compatible storage format with multiple
    CSV files per session for different data types.
    
    Design Principles:
    - All CSV-specific details are hidden here
    - Implements the StorageBackend interface exactly
    - Can be swapped with other backends without changing DataCaptureService
    - Creates organized directory structure with dated folders
    
    File Structure:
    - captures/YYYY-MM-DD/HH-MM-SS_session_XXXX/
      - metadata.json          # Session metadata and configuration
      - predictions.csv        # All prediction data (flattened)
      - opensky_data.csv       # All OpenSky data (flattened)
      - statistics.csv         # Kalman filter statistics over time
    """
    
    def __init__(
        self,
        base_dir: str = "captures",
        session_duration: float = 3600.0,  # 1 hour
        max_file_size: int = 1024 * 1024 * 1024,  # 1 GB
    ):
        """
        Initialize CSV storage backend.
        
        Args:
            base_dir: Base directory for capture files
            session_duration: Maximum session duration in seconds
            max_file_size: Maximum file size in bytes (for rotation check)
        """
        self.base_dir = base_dir
        self.session_duration = session_duration
        self.max_file_size = max_file_size
        
        # Internal state
        self._current_dir_path: Optional[str] = None
        self._current_session_id: Optional[str] = None
        self._start_time: float = 0.0
        self._frame_count: int = 0
        self._total_frames: int = 0
        self._file_handles: Dict[str, Any] = {}
        self._csv_writers: Dict[str, Any] = {}
        
        # Get logger (lazy import to avoid circular dependency)
        from utils.logger import get_logger
        self._logger = get_logger("STORAGE")
    
    @property
    def current_file_path(self) -> Optional[str]:
        """Get the current session directory path."""
        return self._current_dir_path
    
    @property
    def current_session_id(self) -> Optional[str]:
        """Get the current session ID."""
        return self._current_session_id
    
    def start_session(self) -> None:
        """Start a new CSV capture session."""
        self._close_all_files()
        
        try:
            # Create base directory if needed
            Path(self.base_dir).mkdir(parents=True, exist_ok=True)
            
            # Generate session info
            self._current_session_id = str(uuid.uuid4())
            timestamp = self._get_timestamp_str()
            date_dir = Path(self.base_dir) / self._get_date_str()
            date_dir.mkdir(parents=True, exist_ok=True)
            
            # Create session directory
            session_dirname = f"{timestamp}_session_{self._total_frames:04d}"
            self._current_dir_path = str(date_dir / session_dirname)
            Path(self._current_dir_path).mkdir(parents=True, exist_ok=True)
            
            self._frame_count = 0
            self._start_time = time.time()
            
            # Write metadata
            self._write_metadata()
            
            # Initialize CSV files with headers
            self._initialize_csv_files()
            
            self._logger.info(f"Started CSV session: {self._current_dir_path}")
            
        except Exception as e:
            self._logger.error(f"Error starting CSV session: {e}")
            # Clean up on error
            self._current_dir_path = None
            self._current_session_id = None
            raise
    
    def end_session(self) -> None:
        """End the current CSV session."""
        try:
            # Update metadata with end time
            if self._current_dir_path:
                metadata_path = Path(self._current_dir_path) / "metadata.json"
                if metadata_path.exists():
                    try:
                        with open(metadata_path, 'r') as f:
                            metadata = json.load(f)
                        metadata['capture_end'] = time.time()
                        with open(metadata_path, 'w') as f:
                            json.dump(metadata, f, indent=2)
                    except Exception as e:
                        self._logger.error(f"Error updating end time in metadata: {e}")
                
                self._logger.info(f"Finalized CSV session: {self._current_dir_path}")
        except Exception as e:
            self._logger.error(f"Error finalizing CSV session: {e}")
        
        self._close_all_files()
        self._total_frames += self._frame_count
    
    def write_frame(self, frame_data: FrameData) -> None:
        """Write a frame to the CSV files."""
        if self._current_dir_path is None:
            self.start_session()
            if self._current_dir_path is None:
                return
        
        try:
            self._write_predictions_csv(frame_data)
            self._write_opensky_csv(frame_data)
            self._write_statistics_csv(frame_data)
            self._frame_count += 1
        except Exception as e:
            self._logger.error(f"Error writing frame: {e}")
            # Try to recover by starting new session
            self._logger.warning("Attempting to recover by starting new session")
            self.start_session()
    
    def list_files(self) -> List[str]:
        """List all CSV capture session directories."""
        capture_dir = Path(self.base_dir)
        if not capture_dir.exists():
            return []
        
        try:
            # Find all session directories (those with metadata.json)
            session_dirs = []
            for dir_path in capture_dir.rglob('*'):
                if dir_path.is_dir():
                    metadata_file = dir_path / "metadata.json"
                    if metadata_file.exists():
                        session_dirs.append(str(dir_path))
            return sorted(session_dirs, reverse=True)
        except Exception as e:
            self._logger.error(f"Error listing CSV session directories: {e}")
            return []
    
    def should_rotate(self) -> bool:
        """Check if session should be rotated."""
        # Time-based rotation
        if self._start_time > 0:
            if time.time() - self._start_time > self.session_duration:
                return True
        
        # Size-based rotation - check total size of session directory
        if self._current_dir_path and os.path.exists(self._current_dir_path):
            try:
                total_size = sum(
                    os.path.getsize(str(f)) 
                    for f in Path(self._current_dir_path).rglob('*') 
                    if f.is_file()
                )
                if total_size > self.max_file_size:
                    return True
            except OSError:
                pass
        
        return False
    
    # Internal implementation details (hidden from StorageBackend interface)
    
    def _close_all_files(self) -> None:
        """Close all open file handles."""
        for handle in self._file_handles.values():
            try:
                handle.close()
            except Exception as e:
                self._logger.error(f"Error closing file handle: {e}")
        
        self._file_handles = {}
        self._csv_writers = {}
    
    def _get_timestamp_str(self) -> str:
        """Get formatted timestamp string for directory name."""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    
    def _get_date_str(self) -> str:
        """Get formatted date string for directory."""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d")
    
    def _write_metadata(self) -> None:
        """Write metadata JSON file."""
        if self._current_dir_path is None:
            return
        
        try:
            # Get Kalman filter configuration
            kalman_config = self._get_kalman_config()
            
            # Get default location
            location = self._get_default_location()
            
            metadata = {
                'capture_start': self._start_time,
                'session_id': self._current_session_id,
                'turret_version': '1.0.0',
                'file_format_version': '1.0',
                'format': 'csv',
                'kalman_config': kalman_config,
                'location': location,
            }
            
            metadata_path = Path(self._current_dir_path) / "metadata.json"
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            self._logger.debug("Wrote CSV metadata")
            
        except Exception as e:
            self._logger.error(f"Error writing CSV metadata: {e}")
    
    def _get_kalman_config(self) -> Dict[str, Any]:
        """Get Kalman filter configuration from the service."""
        try:
            # Import here to avoid circular dependency
            from services.kalman_filter_service import kalman_filter_service
            return {
                'data_update_interval': kalman_filter_service.DATA_UPDATE_INTERVAL,
                'prediction_interval': kalman_filter_service.PREDICTION_INTERVAL,
                'max_measurement_age': kalman_filter_service.MAX_MEASUREMENT_AGE,
                'position_process_noise': kalman_filter_service.POSITION_PROCESS_NOISE,
                'velocity_process_noise': kalman_filter_service.VELOCITY_PROCESS_NOISE,
                'position_measurement_noise': kalman_filter_service.POSITION_MEASUREMENT_NOISE,
            }
        except Exception:
            return {}
    
    def _get_default_location(self) -> Dict[str, Any]:
        """Get default location from AircraftService."""
        try:
            from services.aircraft_service import aircraft_service
            return aircraft_service.last_position
        except Exception:
            return {}
    
    def _initialize_csv_files(self) -> None:
        """Initialize CSV files with headers."""
        if self._current_dir_path is None:
            return
        
        try:
            # Predictions CSV header
            predictions_header = [
                'timestamp', 'frame_index', 'session_id',
                'callsign', 'latitude', 'longitude', 'baro_altitude',
                'velocity', 'true_track', 'vertical_rate',
                'covariance_lat', 'covariance_lon', 'covariance_alt',
                'state', 'v_north', 'v_east'
            ]
            
            predictions_path = Path(self._current_dir_path) / "predictions.csv"
            pred_file = open(predictions_path, 'w', newline='')
            self._file_handles['predictions'] = pred_file
            self._csv_writers['predictions'] = csv.DictWriter(
                pred_file, 
                fieldnames=predictions_header,
                extrasaction='ignore'
            )
            self._csv_writers['predictions'].writeheader()
            
            # OpenSky Data CSV header
            opensky_header = [
                'timestamp', 'frame_index', 'session_id',
                'callsign', 'latitude', 'longitude', 'baro_altitude',
                'velocity', 'true_track', 'vertical_rate', 'on_ground',
                'v_north', 'v_east'
            ]
            
            opensky_path = Path(self._current_dir_path) / "opensky_data.csv"
            os_file = open(opensky_path, 'w', newline='')
            self._file_handles['opensky'] = os_file
            self._csv_writers['opensky'] = csv.DictWriter(
                os_file,
                fieldnames=opensky_header,
                extrasaction='ignore'
            )
            self._csv_writers['opensky'].writeheader()
            
            # Statistics CSV header
            stats_header = [
                'timestamp', 'frame_index', 'session_id',
                'track_count', 'prediction_count',
                'total_predictions', 'total_measurements',
                'last_data_update_loop_time', 'mean_data_update_loop_time',
                'last_prediction_loop_time', 'mean_prediction_loop_time'
            ]
            
            stats_path = Path(self._current_dir_path) / "statistics.csv"
            stats_file = open(stats_path, 'w', newline='')
            self._file_handles['statistics'] = stats_file
            self._csv_writers['statistics'] = csv.DictWriter(
                stats_file,
                fieldnames=stats_header,
                extrasaction='ignore'
            )
            self._csv_writers['statistics'].writeheader()
            
            self._logger.debug("Initialized CSV files with headers")
            
        except Exception as e:
            self._logger.error(f"Error initializing CSV files: {e}")
            self._close_all_files()
            raise
    
    def _write_predictions_csv(self, frame_data: FrameData) -> None:
        """Write prediction data to CSV."""
        if self._current_dir_path is None or 'predictions' not in self._csv_writers:
            return
        
        try:
            import math
            predictions = frame_data.predictions
            if not predictions:
                return
            
            for pred in predictions:
                row = {
                    'timestamp': frame_data.timestamp,
                    'frame_index': self._frame_count,
                    'session_id': self._current_session_id,
                    'callsign': pred.get('callsign', 'unknown'),
                    'latitude': float(pred.get('latitude', 0.0)),
                    'longitude': float(pred.get('longitude', 0.0)),
                    'baro_altitude': float(pred.get('baro_altitude', 0.0)),
                    'velocity': float(pred.get('velocity', 0.0)),
                    'true_track': float(pred.get('true_track', 0.0)),
                    'vertical_rate': float(pred.get('vertical_rate', 0.0)),
                    'covariance_lat': float(pred.get('covariance_lat', 0.0)),
                    'covariance_lon': float(pred.get('covariance_lon', 0.0)),
                    'covariance_alt': float(pred.get('covariance_alt', 0.0)),
                    'state': pred.get('state', 'unknown'),
                }
                
                # Calculate velocity components
                velocity = float(pred.get('velocity', 0.0))
                true_track = float(pred.get('true_track', 0.0))
                row['v_north'] = velocity * math.cos(math.radians(true_track))
                row['v_east'] = velocity * math.sin(math.radians(true_track))
                
                self._csv_writers['predictions'].writerow(row)
                
        except Exception as e:
            self._logger.error(f"Error writing predictions CSV: {e}")
    
    def _parse_opensky_data(self, data: Dict[str, Any], callsign: str) -> Dict[str, Any]:
        """
        Parse OpenSky data and apply defaults for missing or None fields.
        
        Args:
            data: Raw OpenSky data dictionary
            callsign: Aircraft callsign for logging context
            
        Returns:
            Dictionary with all fields populated and validated
        """
        # Define expected fields with their default values and types
        numeric_fields = [
            'latitude', 'longitude', 'baro_altitude',
            'velocity', 'true_track', 'vertical_rate'
        ]
        boolean_fields = ['on_ground']
        
        parsed = {}
        
        # Process numeric fields
        for field in numeric_fields:
            value = data.get(field)
            if value is None or value == '':
                self._logger.warning(f"Field '{field}' missing or None for {callsign}, defaulting to 0.0")
                print(f"WARNING: Field '{field}' missing or None for {callsign}, defaulting to 0.0")
                parsed[field] = 0.0
            else:
                try:
                    parsed[field] = float(value)
                except (ValueError, TypeError) as e:
                    self._logger.warning(f"Field '{field}' for {callsign} has invalid value '{value}', defaulting to 0.0")
                    print(f"WARNING: Field '{field}' for {callsign} has invalid value '{value}', defaulting to 0.0")
                    parsed[field] = 0.0
        
        # Process boolean fields
        for field in boolean_fields:
            value = data.get(field)
            if value is None or value == '':
                self._logger.warning(f"Field '{field}' missing or None for {callsign}, defaulting to True")
                print(f"WARNING: Field '{field}' missing or None for {callsign}, defaulting to True")
                parsed[field] = True
            else:
                try:
                    parsed[field] = bool(value)
                except (ValueError, TypeError) as e:
                    self._logger.warning(f"Field '{field}' for {callsign} has invalid value '{value}', defaulting to True")
                    print(f"WARNING: Field '{field}' for {callsign} has invalid value '{value}', defaulting to True")
                    parsed[field] = True
        
        return parsed
    
    def _write_opensky_csv(self, frame_data: FrameData) -> None:
        """Write OpenSky data to CSV."""
        if self._current_dir_path is None or 'opensky' not in self._csv_writers:
            return
        
        try:
            import math
            flight_data = frame_data.flight_data
            if not flight_data:
                return
            
            for callsign, data in flight_data.items():
                # Parse and validate data
                parsed_data = self._parse_opensky_data(data, callsign)
                
                row = {
                    'timestamp': frame_data.timestamp,
                    'frame_index': self._frame_count,
                    'session_id': self._current_session_id,
                    'callsign': callsign,
                    'latitude': parsed_data['latitude'],
                    'longitude': parsed_data['longitude'],
                    'baro_altitude': parsed_data['baro_altitude'],
                    'velocity': parsed_data['velocity'],
                    'true_track': parsed_data['true_track'],
                    'vertical_rate': parsed_data['vertical_rate'],
                    'on_ground': parsed_data['on_ground'],
                }
                
                # Calculate velocity components
                velocity = parsed_data['velocity']
                true_track = parsed_data['true_track']
                row['v_north'] = velocity * math.cos(math.radians(true_track))
                row['v_east'] = velocity * math.sin(math.radians(true_track))
                
                self._csv_writers['opensky'].writerow(row)
                
        except Exception as e:
            self._logger.error(f"Error writing OpenSky CSV: {e}")
    
    def _write_statistics_csv(self, frame_data: FrameData) -> None:
        """Write statistics data to CSV."""
        if self._current_dir_path is None or 'statistics' not in self._csv_writers:
            return
        
        try:
            statistics = frame_data.statistics
            
            row = {
                'timestamp': frame_data.timestamp,
                'frame_index': self._frame_count,
                'session_id': self._current_session_id,
                'track_count': int(statistics.get('track_count', 0)),
                'prediction_count': int(statistics.get('prediction_count', 0)),
                'total_predictions': int(statistics.get('total_predictions', 0)),
                'total_measurements': int(statistics.get('total_measurements', 0)),
                'last_data_update_loop_time': float(statistics.get('last_data_update_loop_time', 0.0)),
                'mean_data_update_loop_time': float(statistics.get('mean_data_update_loop_time', 0.0)),
                'last_prediction_loop_time': float(statistics.get('last_prediction_loop_time', 0.0)),
                'mean_prediction_loop_time': float(statistics.get('mean_prediction_loop_time', 0.0)),
            }
            
            self._csv_writers['statistics'].writerow(row)
            
        except Exception as e:
            self._logger.error(f"Error writing statistics CSV: {e}")


class MockStorageBackend(StorageBackend):
    """
    Mock Storage Backend for Testing.
    
    This implementation stores frames in memory for testing purposes.
    It satisfies the StorageBackend interface without requiring any file I/O.
    """
    
    def __init__(self):
        """Initialize mock storage."""
        self._frames: List[FrameData] = []
        self._current_file_path: Optional[str] = "mock.csv"
        self._current_session_id: Optional[str] = "mock-session-id"
        self._session_start: float = 0.0
        self._logger = None
        
        # Try to get logger
        try:
            from utils.logger import get_logger
            self._logger = get_logger("MOCK_STORAGE")
        except ImportError:
            pass
    
    @property
    def current_file_path(self) -> Optional[str]:
        return self._current_file_path
    
    @property
    def current_session_id(self) -> Optional[str]:
        return self._current_session_id
    
    def start_session(self) -> None:
        """Start new mock session."""
        self._frames = []
        self._session_start = time.time()
        if self._logger:
            self._logger.info("Mock storage session started")
    
    def end_session(self) -> None:
        """End mock session."""
        if self._logger:
            self._logger.info(f"Mock storage session ended with {len(self._frames)} frames")
    
    def write_frame(self, frame_data: FrameData) -> None:
        """Write frame to mock storage."""
        self._frames.append(frame_data)
        if self._logger:
            self._logger.debug(f"Mock storage: wrote frame with {len(frame_data.predictions)} predictions")
    
    def list_files(self) -> List[str]:
        """List mock files."""
        return [self._current_file_path] if self._current_file_path else []
    
    def should_rotate(self) -> bool:
        """Mock rotation check."""
        return False
    
    # Additional methods for testing
    def get_frames(self) -> List[FrameData]:
        """Get all stored frames (for testing only)."""
        return self._frames
    
    def clear(self) -> None:
        """Clear all stored frames (for testing only)."""
        self._frames = []
