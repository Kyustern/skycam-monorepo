"""
Data Capture Service

A deep module that captures aircraft tracking data to files for Jupyter analysis.

Design Principles (from codebase-design skill):
- Small Interface: Only 4 public methods (start, stop, get_status, get_capture_files)
- Deep Implementation: All complexity hidden behind simple interface
- Dependency Injection: Accepts dependencies (kalman_service, storage_backend)
- Seam at Interface: Primary seam is the service interface
- Adapter Pattern: Storage backend can be swapped (HDF5, JSON, Mock)

This service captures:
- Every prediction frame from KalmanFilterService
- Latest OpenSky data for each frame
- Kalman filter statistics for each frame

Output format: CSV (human-readable, widely compatible)
"""

import time
import threading
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Any

from services.aircraft_service import aircraft_service
from services.kalman_filter_service import kalman_filter_service
from utils.logger import get_logger


@dataclass
class CaptureStatus:
    """
    Status of the capture service.
    
    This dataclass provides a clean interface for the service status.
    """
    is_capturing: bool = False
    frames_captured: int = 0
    current_file: Optional[str] = None
    session_id: Optional[str] = None
    last_capture_time: float = 0.0
    capture_start_time: float = 0.0
    elapsed_time: float = 0.0


class DataCaptureService:
    """
    Deep module for capturing aircraft tracking data.
    
    PUBLIC INTERFACE (what callers know):
    - start() - Start capturing
    - stop() - Stop capturing
    - get_status() - Get current status
    - get_capture_files() - List capture files
    
    PRIVATE IMPLEMENTATION (hidden complexity):
    - Background capture thread
    - Storage backend management
    - Session rotation
    - Error handling
    - Data serialization
    
    Design Principles:
    - Small interface, deep implementation (depth)
    - Accept dependencies, don't create them
    - Seam at the service interface
    - Adapter pattern for storage backend
    """
    
    # Configuration - could be moved to config module if needed
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
        
        This follows the principle: "Accept dependencies, don't create them"
        
        Args:
            kalman_service: Source of predictions and statistics.
                           If None, uses global kalman_filter_service.
            aircraft_service_ref: Source of OpenSky data.
                                If None, uses global aircraft_service.
            storage_backend: Storage adapter (StorageBackend implementation).
                           If None, creates CSVStorageBackend.
        """
        # Accept dependencies (don't create them)
        self.kalman_service = kalman_service or kalman_filter_service
        self.aircraft_service = aircraft_service_ref or aircraft_service
        self.storage = storage_backend or self._create_default_storage()
        
        # Get logger
        self.logger = get_logger("CAPTURE")
        
        # Internal state (hidden from callers)
        self._lock = threading.Lock()
        self._shutdown_flag = threading.Event()
        self._capture_thread: Optional[threading.Thread] = None
        self._status = CaptureStatus()
    
    def _create_default_storage(self):
        """
        Create default CSV storage backend.
        
        Lazy import to avoid circular dependency and dependency issues.
        """
        try:
            from .storage_backends import CSVStorageBackend
            return CSVStorageBackend(
                base_dir=self.CAPTURE_DIR,
                session_duration=self.SESSION_DURATION,
                max_file_size=self.MAX_FILE_SIZE,
            )
        except ImportError as e:
            self.logger.error(f"Failed to import CSVStorageBackend: {e}")
            # Fallback to mock for testing
            from .storage_backends import MockStorageBackend
            return MockStorageBackend()
    
    # =========================================================================
    # PUBLIC INTERFACE - Small and focused
    # =========================================================================
    
    def start(self) -> None:
        """
        Start the capture service.
        
        Hides complexity:
        - Session initialization
        - Thread creation and management
        - Storage backend setup
        - Error handling
        
        This is the primary seam where callers interact with the service.
        """
        with self._lock:
            if self._status.is_capturing:
                self.logger.warning("Capture service already running")
                return
            
            try:
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
                self._status = CaptureStatus(
                    is_capturing=True,
                    frames_captured=0,
                    current_file=self.storage.current_file_path,
                    session_id=self.storage.current_session_id,
                    last_capture_time=0.0,
                    capture_start_time=time.time(),
                    elapsed_time=0.0,
                )
                
                self.logger.info("Data capture service started")
                
            except Exception as e:
                self.logger.error(f"Error starting capture service: {e}")
                # Clean up on error
                try:
                    self.storage.end_session()
                except:
                    pass
                raise
    
    def stop(self) -> None:
        """
        Stop the capture service.
        
        Hides complexity:
        - Thread cleanup and synchronization
        - Session finalization
        - Storage backend cleanup
        """
        with self._lock:
            if not self._status.is_capturing:
                self.logger.warning("Capture service not running")
                return
            
            self._shutdown_flag.set()
            
            # Wait for thread to finish
            if self._capture_thread and self._capture_thread.is_alive():
                self._capture_thread.join(timeout=2.0)
                if self._capture_thread.is_alive():
                    self.logger.warning("Capture thread did not stop gracefully")
            
            # Finalize session
            try:
                self.storage.end_session()
            except Exception as e:
                self.logger.error(f"Error ending storage session: {e}")
            
            # Update status
            elapsed = time.time() - self._status.capture_start_time
            self._status = CaptureStatus(
                is_capturing=False,
                frames_captured=self._status.frames_captured,
                current_file=self._status.current_file,
                session_id=self._status.session_id,
                last_capture_time=self._status.last_capture_time,
                capture_start_time=self._status.capture_start_time,
                elapsed_time=elapsed,
            )
            
            self.logger.info("Data capture service stopped")
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get current service status.
        
        Returns:
            Dictionary with service status information.
        """
        with self._lock:
            elapsed = time.time() - self._status.capture_start_time if self._status.capture_start_time > 0 else 0
            return {
                **asdict(self._status),
                "elapsed_time": elapsed,
            }
    
    def get_capture_files(self) -> List[str]:
        """
        Get list of all capture files.
        
        Returns:
            List of file paths, newest first.
        """
        return self.storage.list_files()
    
    # =========================================================================
    # PRIVATE IMPLEMENTATION - Hidden complexity
    # =========================================================================
    
    def _capture_loop(self) -> None:
        """
        Background thread that captures data periodically.
        
        This is part of the hidden implementation. Callers don't need to know
        about this method - they only interact through start() and stop().
        """
        self.logger.info("Capture loop started")
        
        while not self._shutdown_flag.is_set():
            start_time = time.time()
            
            try:
                self._capture_frame()
                
                with self._lock:
                    self._status = CaptureStatus(
                        is_capturing=self._status.is_capturing,
                        frames_captured=self._status.frames_captured + 1,
                        current_file=self._status.current_file,
                        session_id=self._status.session_id,
                        last_capture_time=start_time,
                        capture_start_time=self._status.capture_start_time,
                        elapsed_time=0.0,
                    )
                
                # Check for session rotation
                if self.storage.should_rotate():
                    self.logger.info("Rotating to new session (time/size limit)")
                    self.storage.start_session()
                    with self._lock:
                        self._status = CaptureStatus(
                            is_capturing=self._status.is_capturing,
                            frames_captured=self._status.frames_captured,
                            current_file=self.storage.current_file_path,
                            session_id=self.storage.current_session_id,
                            last_capture_time=self._status.last_capture_time,
                            capture_start_time=self._status.capture_start_time,
                            elapsed_time=0.0,
                        )
                
            except Exception as e:
                self.logger.error(f"Error in capture loop: {e}")
                # Continue looping - don't let one error stop the service
            
            # Sleep until next capture (aligned with Kalman prediction interval)
            self._sleep_until_next_capture(start_time)
        
        self.logger.info("Capture loop stopped")
    
    def _capture_frame(self) -> None:
        """
        Capture a single frame of data.
        
        Builds frame data from:
        - KalmanFilterService predictions
        - KalmanFilterService latest flight data
        - KalmanFilterService statistics
        
        Then delegates to storage backend to write the frame.
        """
        # Import FrameData here to avoid circular dependency
        from .storage_backends import FrameData
        
        # Get data from services (using public methods where possible)
        predictions = self.kalman_service.get_latest_predictions()
        flight_data = self._get_current_flight_data()
        statistics = self.kalman_service.get_statistics()
        
        # Build frame data as FrameData dataclass
        frame_data = FrameData(
            timestamp=time.time(),
            predictions=predictions,
            flight_data=flight_data,
            statistics=statistics,
        )
        
        # Write to storage (delegate to backend)
        self.storage.write_frame(frame_data)
    
    def _get_current_flight_data(self) -> Dict[str, Dict]:
        """
        Get current flight data from Kalman filter service.
        
        Note: This accesses the internal _latest_flight_data which is set by
        the KalmanFilterService when it updates from AircraftService.
        
        This is a deliberate design choice: the KalmanFilterService already
        maintains this data, so we don't need to duplicate the fetching logic.
        """
        # Access the latest flight data that was stored by KalmanFilterService
        # This is the data that was most recently fetched from OpenSky
        if hasattr(self.kalman_service, '_latest_flight_data'):
            return self.kalman_service._latest_flight_data
        return {}
    
    def _sleep_until_next_capture(self, start_time: float) -> None:
        """
        Sleep until the next capture time.
        
        Aligns with the Kalman filter's PREDICTION_INTERVAL to ensure
        we capture every prediction frame.
        """
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


# Global service instance (singleton pattern)
data_capture_service = DataCaptureService()
