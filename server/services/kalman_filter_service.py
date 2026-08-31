"""
Kalman Filter Service
Provides position prediction for aircraft using Kalman filtering.
Uses data from the AircraftService to track and predict flight positions.
"""
import math
import threading
import time
from typing import Dict, Optional, List, Tuple
from dataclasses import dataclass, field
from enum import Enum
import numpy as np
from socketio_instance import get_socketio

from services.aircraft_service import aircraft_service
from utils.logger import kalman_logger


class KalmanFilterState(Enum):
    """State of the Kalman filter for a flight."""
    INITIALIZING = "initializing"
    TRACKING = "tracking"
    LOST = "lost"


@dataclass
class FlightPrediction:
    """Predicted flight state at a given time."""
    callsign: str
    latitude: float
    longitude: float
    baro_altitude: float
    velocity: float
    true_track: float
    vertical_rate: float
    timestamp: float
    covariance_lat: float
    covariance_lon: float
    covariance_alt: float
    state: KalmanFilterState
    icao: str = ""
    origin_country: str = ""
    on_ground: bool = False
    
    def to_dict(self) -> Dict:
        """Convert prediction to dictionary for JSON serialization."""
        return {
            "callsign": self.callsign,
            "icao": self.icao,
            "origin_country": self.origin_country,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "baro_altitude": self.baro_altitude,
            "baro_altitude_km": self.baro_altitude / 1000,
            "velocity": self.velocity,
            "true_track": self.true_track,
            "vertical_rate": self.vertical_rate,
            "timestamp": self.timestamp,
            "covariance_lat": self.covariance_lat,
            "covariance_lon": self.covariance_lon,
            "covariance_alt": self.covariance_alt,
            "state": self.state.value,
            "on_ground": self.on_ground,
        }


@dataclass
class FlightTrack:
    """Tracks the Kalman filter state for a single flight."""
    callsign: str
    icao: str
    origin_country: str
    
    # Kalman filter state vector: [north, east, alt, v_north, v_east, v_alt]
    # All positions in meters (relative to reference point), velocities in m/s
    state_vector: np.ndarray = field(default_factory=lambda: np.zeros(6))
    covariance_matrix: np.ndarray = field(default_factory=lambda: np.eye(6))
    
    # Reference point for coordinate conversion (degrees)
    ref_latitude: float = 0.0
    ref_longitude: float = 0.0
    
    # Last measurement timestamp
    last_measurement_time: float = 0.0
    
    # Filter state
    filter_state: KalmanFilterState = KalmanFilterState.INITIALIZING
    
    # Process noise covariance (tuned for flight dynamics)
    Q: np.ndarray = field(default_factory=lambda: np.eye(6))
    
    # Measurement noise covariance
    R: np.ndarray = field(default_factory=lambda: np.eye(3))
    
    # Prediction timestamp
    last_prediction_time: float = 0.0
    
    # Track history for debugging
    predictions: List[FlightPrediction] = field(default_factory=list)
    
    def __post_init__(self):
        """Initialize with proper matrices."""
        # Initialize matrices if they're zero-sized
        if self.state_vector.size == 0:
            self.state_vector = np.zeros(6)
        if self.covariance_matrix.size == 0:
            self.covariance_matrix = np.eye(6)
        if self.Q.size == 0:
            self.Q = np.eye(6)
        if self.R.size == 0:
            self.R = np.eye(3)
        
        # Ensure state_vector is always float64 (not object dtype with None values)
        if self.state_vector.dtype == object:
            # Replace None values with 0.0
            self.state_vector = np.array([float(x) if x is not None else 0.0 for x in self.state_vector], dtype=np.float64)


class KalmanFilterService:
    """
    Service that uses Kalman filters to track and predict aircraft positions.
    
    Features:
    - Fetches new aircraft data every 5 seconds from AircraftService
    - Maintains a Kalman filter for each tracked flight
    - Predicts positions every 500ms
    - Handles flight appearance/disappearance
    - Provides smooth, continuous position predictions
    """
    
    # Earth radius in meters
    EARTH_RADIUS = 6371000.0

    #Update timers in seconds : 
    # Update interval for fetching new data
    DATA_UPDATE_INTERVAL = 30.0
    
    # Prediction interval
    PREDICTION_INTERVAL = 2.0
    
    # Maximum time without measurement before marking as lost (30 seconds)
    MAX_MEASUREMENT_AGE = 60.0
    
    # Process noise tuning parameters
    POSITION_PROCESS_NOISE = 100.0    # meters^2/s^3
    VELOCITY_PROCESS_NOISE = 200.0     # (m/s)^2/s
    
    # Measurement noise tuning (GPS typical accuracy)
    POSITION_MEASUREMENT_NOISE = 20.0  # meters^2
    
    def __init__(self, aircraft_service_ref=None):
        """
        Initialize the Kalman filter service.
        
        Args:
            aircraft_service_ref: Reference to AircraftService (defaults to global instance)
        """
        self.AIRCRAFT_SERVICE = aircraft_service_ref or aircraft_service
        self._get_socketio = get_socketio

        
        # Track dictionary: callsign -> FlightTrack
        self._tracks: Dict[str, FlightTrack] = {}
        
        # Thread control
        self._shutdown_flag = threading.Event()
        self._lock = threading.Lock()
        
        # Latest predictions for API access
        self._latest_predictions: Dict[str, FlightPrediction] = {}

        # Latest openssky API data
        self._latest_flight_data: Dict[str, Dict] = {}
        
        # Data update thread
        self._data_update_thread: Optional[threading.Thread] = None
        
        # Prediction thread
        self._prediction_thread: Optional[threading.Thread] = None
        
        # Timing
        self._last_data_update = 0.0
        self._last_prediction = 0.0
        
        # Loop timing tracking for analysis
        self._data_update_times: List[float] = []  # Execution times of data update loops
        self._prediction_times: List[float] = []  # Execution times of prediction loops
        
        # Statistics
        self._total_predictions = 0
        self._total_measurements = 0

    def _get_current_time(self) -> float:
        """Get current timestamp."""
        return time.time()
    
    def _get_float(self, value, default: float = 0.0) -> float:
        """
        Safely extract a float value, returning default if value is None.
        
        Args:
            value: The value to convert
            default: Default value if value is None
            
        Returns:
            Float value (or default if None)
        """
        return default if value is None else float(value)

    def _degrees_to_meters(self, lat: float, delta_lat: float, delta_lon: float) -> Tuple[float, float]:
        """
        Convert latitude/longitude deltas to meters.
        
        Args:
            lat: Reference latitude in degrees
            delta_lat: Latitude delta in degrees
            delta_lon: Longitude delta in degrees
            
        Returns:
            Tuple of (delta_north, delta_east) in meters
        """
        # 1 degree of latitude = pi/180 * Earth radius
        meters_per_deg_lat = math.pi * self.EARTH_RADIUS / 180.0
        
        # 1 degree of longitude = meters_per_deg_lat * cos(latitude)
        meters_per_deg_lon = meters_per_deg_lat * abs(math.cos(math.radians(lat)))
        
        return (
            delta_lat * meters_per_deg_lat,
            delta_lon * meters_per_deg_lon
        )

    def _meters_to_degrees(self, lat: float, delta_north: float, delta_east: float) -> Tuple[float, float]:
        """
        Convert meter deltas to latitude/longitude deltas.
        
        Args:
            lat: Reference latitude in degrees
            delta_north: North delta in meters
            delta_east: East delta in meters
            
        Returns:
            Tuple of (delta_lat, delta_lon) in degrees
        """
        meters_per_deg_lat = math.pi * self.EARTH_RADIUS / 180.0
        meters_per_deg_lon = meters_per_deg_lat * abs(math.cos(math.radians(lat)))
        
        return (
            delta_north / meters_per_deg_lat,
            delta_east / meters_per_deg_lon if meters_per_deg_lon > 0 else 0
        )

    def _create_flight_track(self, flight_data: Dict) -> FlightTrack:
        """
        Create a new FlightTrack for a detected aircraft.
        
        Args:
            flight_data: Raw flight data from OpenSky API
            
        Returns:
            New FlightTrack instance
        """
        callsign = flight_data.get("callsign", "").strip()
        icao = flight_data.get("icao", "")
        origin_country = flight_data.get("origin_country", "")
        
        # Get initial position (handle None values from API)
        lat = self._get_float(flight_data.get("latitude"), 0.0)
        lon = self._get_float(flight_data.get("longitude"), 0.0)
        alt = self._get_float(flight_data.get("baro_altitude"), 0.0)  # in meters
        
        # Use initial position as reference point
        ref_lat = lat
        ref_lon = lon
        
        # Convert initial position to meters relative to reference (should be 0,0)
        north_0, east_0 = self._degrees_to_meters(ref_lat, 0, 0)
        
        track = FlightTrack(
            callsign=callsign,
            icao=icao,
            origin_country=origin_country,
            ref_latitude=ref_lat,
            ref_longitude=ref_lon,
            last_measurement_time=self._get_current_time(),
            filter_state=KalmanFilterState.INITIALIZING
        )
        
        # Velocity in m/s (assuming velocity is in m/s from OpenSky)
        velocity = self._get_float(flight_data.get("velocity"), 0.0)
        
        # Convert velocity and heading to north/east components
        true_track = self._get_float(flight_data.get("true_track"), 0.0)  # in degrees, 0 = north
        velocity_north = velocity * math.cos(math.radians(true_track))
        velocity_east = velocity * math.sin(math.radians(true_track))
        
        # Vertical rate (assuming in m/s, positive = climbing)
        vertical_rate = self._get_float(flight_data.get("vertical_rate"), 0.0)
        
        # Initial state: [north, east, alt, v_north, v_east, v_alt]
        # All positions in meters relative to reference point
        track.state_vector = np.array([
            0.0,  # north (0 at reference point)
            0.0,  # east (0 at reference point)
            alt,  # altitude in meters
            velocity_north,
            velocity_east,
            vertical_rate
        ])
        
        # Initialize covariance matrix (high uncertainty initially)
        # Position uncertainty: 1000m^2, Velocity uncertainty: 100 (m/s)^2
        position_var = 1000.0
        velocity_var = 200.0
        altitude_var = 1000.0
        vertical_velocity_var = 100.0
        
        track.covariance_matrix = np.diag([
            position_var, position_var, altitude_var,
            velocity_var, velocity_var, vertical_velocity_var
        ])
        
        # Process noise covariance
        track.Q = np.diag([
            self.POSITION_PROCESS_NOISE, self.POSITION_PROCESS_NOISE, self.POSITION_PROCESS_NOISE,
            self.VELOCITY_PROCESS_NOISE, self.VELOCITY_PROCESS_NOISE, self.VELOCITY_PROCESS_NOISE
        ])
        
        # Measurement noise covariance (only for position measurements)
        track.R = np.diag([
            self.POSITION_MEASUREMENT_NOISE,
            self.POSITION_MEASUREMENT_NOISE,
            self.POSITION_MEASUREMENT_NOISE
        ])
        
        return track

    def _initialize_new_tracks(self, flights: Dict[str, Dict]) -> int:
        """
        Initialize Kalman filter tracks for new flights.
        
        Args:
            flights: Dictionary of callsign -> flight data
            
        Returns:
            Number of new tracks created
        """
        new_tracks = 0
        
        for callsign, flight_data in flights.items():
            if callsign not in self._tracks:
                # Skip ground vehicles
                if flight_data.get("on_ground", True):
                    continue
                    
                track = self._create_flight_track(flight_data)
                self._tracks[callsign] = track
                new_tracks += 1
                
        return new_tracks

    def _remove_lost_tracks(self) -> int:
        """
        Remove tracks that haven't been updated for too long.
        
        Returns:
            Number of tracks removed
        """
        removed = 0
        current_time = self._get_current_time()
        
        lost_callsign = []
        for callsign, track in self._tracks.items():
            age = current_time - track.last_measurement_time
            if age > self.MAX_MEASUREMENT_AGE:
                lost_callsign.append(callsign)
                
        for callsign in lost_callsign:
            del self._tracks[callsign]
            if callsign in self._latest_predictions:
                del self._latest_predictions[callsign]
            removed += 1
            
        return removed

    def _update_track_with_measurement(self, track: FlightTrack, flight_data: Dict) -> bool:
        """
        Update a track with new measurement data using Kalman filter update step.
        
        Args:
            track: The FlightTrack to update
            flight_data: New measurement data
            
        Returns:
            True if update was successful
        """
        current_time = self._get_current_time()
        dt = current_time - track.last_measurement_time
        
        # Skip if time delta is too small or negative
        if dt <= 0:
            track.last_measurement_time = current_time
            return False
        
        # Measurement vector: [north, east, alt] in meters relative to track's reference point
        lat_meas = self._get_float(flight_data.get("latitude"), 0.0)
        lon_meas = self._get_float(flight_data.get("longitude"), 0.0)
        alt_meas = self._get_float(flight_data.get("baro_altitude"), 0.0)
        
        # Convert lat/lon to meters relative to track's reference point
        north_meas, east_meas = self._degrees_to_meters(
            track.ref_latitude, 
            lat_meas - track.ref_latitude, 
            lon_meas - track.ref_longitude
        )
        
        z = np.array([north_meas, east_meas, alt_meas])
        
        # First, predict to current time
        self._predict_track(track, current_time)
        
        # State vector after prediction: [north_pred, east_pred, alt_pred, v_north, v_east, v_alt]
        x_pred = track.state_vector.copy()
        P_pred = track.covariance_matrix.copy()
        
        # Measurement matrix H: maps state to measurement
        # H = [1 0 0 0 0 0]  # north
        #     [0 1 0 0 0 0]  # east
        #     [0 0 1 0 0 0]  # alt
        H = np.array([
            [1, 0, 0, 0, 0, 0],
            [0, 1, 0, 0, 0, 0],
            [0, 0, 1, 0, 0, 0]
        ])
        
        # Measurement residual: y = z - H * x_pred
        y = z - H @ x_pred
        
        # Innovation covariance: S = H * P_pred * H^T + R
        S = H @ P_pred @ H.T + track.R
        
        # Kalman gain: K = P_pred * H^T * S^-1
        try:
            S_inv = np.linalg.inv(S)
        except np.linalg.LinAlgError:
            # S is singular, can't update
            track.last_measurement_time = current_time
            return False
            
        K = P_pred @ H.T @ S_inv
        
        # Update state: x = x_pred + K * y
        track.state_vector = x_pred + K @ y
        
        # Update covariance: P = (I - K * H) * P_pred
        I = np.eye(6)
        track.covariance_matrix = (I - K @ H) @ P_pred
        
        # Update track state
        track.last_measurement_time = current_time
        if track.filter_state == KalmanFilterState.INITIALIZING:
            track.filter_state = KalmanFilterState.TRACKING
            
        return True

    def _predict_track(self, track: FlightTrack, predict_time: float) -> FlightPrediction:
        """
        Predict the position of a track at a given time using Kalman filter prediction step.
        
        Args:
            track: The FlightTrack to predict
            predict_time: The time to predict to
            
        Returns:
            FlightPrediction with the predicted state
        """
        current_time = self._get_current_time()
        dt = predict_time - track.last_measurement_time
        
        # Clamp dt to not go backwards in time
        dt = max(dt, 0)
        
        # Ensure state_vector is float64 (safeguard against None values)
        if track.state_vector.dtype == object:
            track.state_vector = np.array([float(x) if x is not None else 0.0 for x in track.state_vector], dtype=np.float64)
        
        # State transition matrix F (constant velocity model)
        # F = [1 0 0 dt 0  0 ]  # north += v_north * dt
        #     [0 1 0 0  dt 0 ]  # east += v_east * dt
        #     [0 0 1 0  0  dt]  # alt += v_alt * dt
        #     [0 0 0 1  0  0 ]  # v_north stays the same
        #     [0 0 0 0  1  0 ]  # v_east stays the same
        #     [0 0 0 0  0  1 ]  # v_alt stays the same
        F = np.array([
            [1, 0, 0, dt, 0,  0],
            [0, 1, 0, 0,  dt, 0],
            [0, 0, 1, 0,  0,  dt],
            [0, 0, 0, 1,  0,  0],
            [0, 0, 0, 0,  1,  0],
            [0, 0, 0, 0,  0,  1]
        ])
        
        # Predicted state: x_pred = F * x
        x_pred = F @ track.state_vector
        
        # Predicted covariance: P_pred = F * P * F^T + Q
        P_pred = F @ track.covariance_matrix @ F.T + track.Q
        
        # Extract predicted values (all in meters or m/s)
        pred_north = x_pred[0]   # meters relative to reference
        pred_east = x_pred[1]     # meters relative to reference
        pred_alt = x_pred[2]      # meters
        pred_v_north = x_pred[3] # m/s
        pred_v_east = x_pred[4]  # m/s
        pred_v_alt = x_pred[5]   # m/s
        
        # Convert north/east back to lat/lon relative to reference point
        delta_lat, delta_lon = self._meters_to_degrees(
            track.ref_latitude, pred_north, pred_east
        )
        
        pred_lat = track.ref_latitude + delta_lat
        pred_lon = track.ref_longitude + delta_lon
        
        # Convert velocity components back to speed and heading
        velocity = math.sqrt(pred_v_north**2 + pred_v_east**2)
        if velocity > 0:
            true_track = math.degrees(math.atan2(pred_v_east, pred_v_north))
            true_track = true_track % 360
        else:
            true_track = 0.0
            
        # Convert position covariance from meters^2 to degrees^2 for output
        # This is approximate - covariance in lat/lon is not perfectly accurate due to earth curvature
        meters_per_deg_lat = math.pi * self.EARTH_RADIUS / 180.0
        meters_per_deg_lon = meters_per_deg_lat * abs(math.cos(math.radians(track.ref_latitude)))
        
        cov_lat_deg = P_pred[0, 0] / (meters_per_deg_lat ** 2)
        cov_lon_deg = P_pred[1, 1] / (meters_per_deg_lon ** 2) if meters_per_deg_lon > 0 else P_pred[1, 1]
        cov_alt_m = P_pred[2, 2]  # altitude covariance in m^2
        
        # Create prediction
        prediction = FlightPrediction(
            callsign=track.callsign,
            icao=track.icao,
            origin_country=track.origin_country,
            latitude=float(pred_lat),
            longitude=float(pred_lon),
            baro_altitude=float(pred_alt),
            velocity=float(velocity),
            true_track=float(true_track),
            vertical_rate=float(pred_v_alt),
            timestamp=predict_time,
            covariance_lat=float(cov_lat_deg),
            covariance_lon=float(cov_lon_deg),
            covariance_alt=float(cov_alt_m),
            state=track.filter_state,
            on_ground=False
        )
        
        return prediction

    def _generate_predictions(self, predict_time: float) -> Dict[str, FlightPrediction]:
        """
        Generate predictions for all active tracks.
        
        Args:
            predict_time: The time to predict to
            
        Returns:
            Dictionary of callsign -> FlightPrediction
        """
        predictions = {}
        
        for callsign, track in self._tracks.items():
            try:
                prediction = self._predict_track(track, predict_time)
                predictions[callsign] = prediction
                # self._get_socketio().emit("prediction_data", predictions, callback=lambda: 
                #     kalman_logger.debug(f"Sent latest prediction data with {len(list(predictions.values()))} flights")
                # )                
            except Exception as e:
                # Skip tracks that fail to predict
                kalman_logger.error(f"Error predicting for {callsign}: {e}")
                kalman_logger.debug(f"Track state: {track}")

        return predictions

    def update_from_aircraft_service(self) -> Dict[str, Dict]:
        """
        Fetch new aircraft data and update all tracks.
        
        Returns:
            Dictionary of callsign -> flight data
        """
        try:
            # Fetch new data from OpenSky
            data = self.AIRCRAFT_SERVICE.get_aircraft_at_last_pos()

            # Parse the response
            flights = self._parse_opensky_response(data)

            self._latest_flight_data = flights
            # self._latest_flight_data = list(flights.values())

            self._get_socketio().emit("aircraft_data", flights, callback=lambda: 
                kalman_logger.debug(f"Sent latest flight data with {len(list(flights.values()))} flights")
            )
            
            if not flights:
                return {}
                
            with self._lock:
                # Initialize new tracks for new flights
                new_tracks = self._initialize_new_tracks(flights)
                
                # Update existing tracks with new measurements
                updated_tracks = 0
                for callsign, flight_data in flights.items():
                    if callsign in self._tracks:
                        track = self._tracks[callsign]
                        if self._update_track_with_measurement(track, flight_data):
                            updated_tracks += 1
                            self._total_measurements += 1
                
                #TODO: Remove or store under speparate state the flights gone away from the range
                removed_tracks = self._remove_lost_tracks()
                
                self._total_measurements += new_tracks
                
                return flights
                
        except Exception as e:
            kalman_logger.error(f"Error updating from aircraft service: {e}")
            return {}

    def _parse_opensky_response(self, data: Dict) -> Dict[str, Dict]:
        """
        Parse OpenSky API response into flight dictionary.
        
        Args:
            data: Raw response from OpenSky API
            
        Returns:
            Dictionary of callsign -> flight data
        """
        flights = {}
        
        if not data or "states" not in data:
            return flights
            
        states = data.get("states", [])
        if not states or states is None:
            return flights
            
        # OpenSky returns states as a list of lists
        # Each state has: [icao24, callsign, origin_country, time_position, last_contact,
        #                  longitude, latitude, baro_altitude, on_ground, velocity, true_track,
        #                  vertical_rate, sensors, geo_altitude, squawk, spi, position_source]
        
        STATE_KEYS = [
            "icao", "callsign", "origin_country", "time_position", "last_contact",
            "longitude", "latitude", "baro_altitude", "on_ground", "velocity",
            "true_track", "vertical_rate", "sensors", "geo_altitude", "squawk",
            "spi", "position_source"
        ]
        
        for state in states:
            if not state or not isinstance(state, (list, tuple)):
                continue
                
            flight_data = {}
            for i, key in enumerate(STATE_KEYS):
                if i < len(state):
                    flight_data[key] = state[i]
                else:
                    flight_data[key] = None
            
            # Extract callsign and clean it
            callsign = flight_data.get("callsign", "")
            if callsign:
                callsign = callsign.strip()
                flight_data["callsign"] = callsign
                
                # Only include airborne aircraft
                if not flight_data.get("on_ground", True):
                    flights[callsign] = flight_data
                    
        return flights

    def _data_update_loop(self):
        """Background thread to fetch new data periodically."""
        kalman_logger.info("Starting data update thread...")
        
        while not self._shutdown_flag.is_set():
            start_time = self._get_current_time()
            
            try:
                updated_data = self.update_from_aircraft_service()
                updated_data_count = len(updated_data.items())
                self._last_data_update = self._get_current_time()
                
                # Record loop execution time
                loop_duration = self._last_data_update - start_time
                self._data_update_times.append(loop_duration)
                
                if updated_data_count > 0:
                    kalman_logger.info(f"Updated {updated_data_count} flights at {self._last_data_update:.2f}")

            except Exception as e:
                kalman_logger.error(f"Error in data update loop: {e}")
                
            # Sleep for the remaining interval
            elapsed = self._get_current_time() - start_time
            sleep_time = max(0, self.DATA_UPDATE_INTERVAL - elapsed)
            
            # Wait with periodic checks for shutdown
            wait_start = self._get_current_time()
            while not self._shutdown_flag.is_set() and (self._get_current_time() - wait_start) < sleep_time:
                time.sleep(0.001)
                
    def _prediction_loop(self):
        """Background thread to generate predictions periodically."""
        kalman_logger.info("Starting prediction thread...")
        
        while not self._shutdown_flag.is_set():
            start_time = self._get_current_time()
            predict_time = start_time + self.PREDICTION_INTERVAL
            
            try:
                # Generate predictions for all tracks
                with self._lock:
                    predictions = self._generate_predictions(predict_time)
                    self._latest_predictions = predictions
                    self._last_prediction = start_time
                    self._total_predictions += len(predictions)

                latest_preds = self.get_latest_predictions()
                self._get_socketio().emit("prediction_data", latest_preds)
                
                # Record loop execution time
                loop_duration = self._get_current_time() - start_time
                self._prediction_times.append(loop_duration)
                    
                # Log every prediction cycle
                kalman_logger.info(f"Generated {len(predictions)} predictions at {start_time:.2f}")
                    
            except Exception as e:
                kalman_logger.error(f"Error in prediction loop: {e}")
                
            # Sleep for the remaining interval
            elapsed = self._get_current_time() - start_time
            sleep_time = max(0, self.PREDICTION_INTERVAL - elapsed)
            
            # Wait with periodic checks for shutdown
            wait_start = self._get_current_time()
            while not self._shutdown_flag.is_set() and (self._get_current_time() - wait_start) < sleep_time:
                time.sleep(0.01)  # Shorter sleep for more responsive shutdown

    def get_latest_predictions(self) -> List[Dict]:
        """
        Get the latest predictions for all tracked flights as a list.
        
        Returns:
            List of prediction dictionaries with callsign included
        """
        with self._lock:
            return [
                {**prediction.to_dict(), "callsign": callsign}
                for callsign, prediction in self._latest_predictions.items()
            ]

    def get_prediction_for_flight(self, callsign: str) -> Optional[Dict]:
        """
        Get the latest prediction for a specific flight.
        
        Args:
            callsign: The flight callsign
            
        Returns:
            Prediction data as dictionary, or None if not found
        """
        with self._lock:
            if callsign in self._latest_predictions:
                return self._latest_predictions[callsign].to_dict()
            return None

    def get_track_count(self) -> int:
        """Get the number of currently tracked flights."""
        with self._lock:
            return len(self._tracks)
    
    def is_running(self) -> bool:
        """Check if the service is currently running (both threads alive)."""
        return (self._data_update_thread is not None and self._data_update_thread.is_alive()) and \
               (self._prediction_thread is not None and self._prediction_thread.is_alive())

    def get_statistics(self) -> Dict:
        """Get service statistics."""
        with self._lock:
            current_time = self._get_current_time()
            stats = {
                "track_count": len(self._tracks),
                "prediction_count": len(self._latest_predictions),
                "total_predictions": self._total_predictions,
                "total_measurements": self._total_measurements,
                "last_data_update": self._last_data_update,
                "last_prediction": self._last_prediction,
                "data_update_interval": self.DATA_UPDATE_INTERVAL,
                "prediction_interval": self.PREDICTION_INTERVAL,
                "time_since_last_update": current_time - self._last_data_update if self._last_data_update > 0 else 0,
                "time_since_last_prediction": current_time - self._last_prediction if self._last_prediction > 0 else 0,
                "data_thread_alive": self._data_update_thread is not None and self._data_update_thread.is_alive(),
                "prediction_thread_alive": self._prediction_thread is not None and self._prediction_thread.is_alive(),
            }
            
            # Add loop timing data to statistics
            if self._data_update_times:
                stats["last_data_update_loop_time"] = self._data_update_times[-1]
                stats["mean_data_update_loop_time"] = float(np.mean(self._data_update_times))
            if self._prediction_times:
                stats["last_prediction_loop_time"] = self._prediction_times[-1]
                stats["mean_prediction_loop_time"] = float(np.mean(self._prediction_times))
            
            return stats
    
    def get_loop_timing_data(self) -> Dict[str, List[float]]:
        """
        Get timing data for both loop threads.
        
        Returns:
            Dictionary with 'data_update_times' and 'prediction_times' lists
            containing execution durations in seconds for each loop iteration
        """
        with self._lock:
            return {
                "data_update_times": list(self._data_update_times),
                "prediction_times": list(self._prediction_times)
            }
    
    def clear_loop_timing_data(self) -> None:
        """Clear the stored loop timing data."""
        with self._lock:
            self._data_update_times.clear()
            self._prediction_times.clear()

    def start(self):
        """Start the Kalman filter service threads."""
        # Check if already running
        if (self._data_update_thread is not None and self._data_update_thread.is_alive()) or \
           (self._prediction_thread is not None and self._prediction_thread.is_alive()):
            kalman_logger.warning("Service is already running, skipping duplicate start")
            return
        
        kalman_logger.info("Starting Kalman filter service...")
        
        self._shutdown_flag.clear()
        
        # Start data update thread
        self._data_update_thread = threading.Thread(
            target=self._data_update_loop,
            daemon=True,
            name="kalman-data-update"
        )
        self._data_update_thread.start()
        
        # Start prediction thread
        self._prediction_thread = threading.Thread(
            target=self._prediction_loop,
            daemon=True,
            name="kalman-prediction"
        )
        self._prediction_thread.start()
        
        kalman_logger.info("Service started successfully")

    def stop(self):
        """Stop the Kalman filter service threads."""
        kalman_logger.info("Stopping Kalman filter service...")
        
        self._shutdown_flag.set()
        
        # Wait for threads to finish
        if self._data_update_thread and self._data_update_thread.is_alive():
            self._data_update_thread.join(timeout=self.DATA_UPDATE_INTERVAL)
            
        if self._prediction_thread and self._prediction_thread.is_alive():
            self._prediction_thread.join(timeout=self.PREDICTION_INTERVAL)

        
        # Reset thread references after stopping
        self._data_update_thread = None
        self._prediction_thread = None
            
        kalman_logger.info("Service stopped")


# Global service instance
kalman_filter_service = KalmanFilterService()
