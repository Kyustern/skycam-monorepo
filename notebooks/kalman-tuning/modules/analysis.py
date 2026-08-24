"""
Analysis Module for Kalman Filter Analysis

This module provides comprehensive analysis functions for TURRET captured data,
including aircraft tracking analysis, Kalman filter performance metrics,
statistical analysis, temporal analysis, and configuration analysis.

Author: TURRET Analysis System
Version: 1.0.0
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from scipy import stats
from scipy.spatial.distance import cdist
import math


# Earth radius in meters (for distance calculations)
EARTH_RADIUS = 6371000.0


@dataclass
class TrackContinuityMetrics:
    """Metrics for track continuity analysis."""
    callsign: str
    total_frames: int
    continuous_segments: int
    max_gap_frames: int
    avg_gap_frames: float
    total_gap_time: float
    track_coverage: float  # Percentage of time tracked


@dataclass
class PredictionErrorMetrics:
    """Metrics for prediction error analysis."""
    callsign: str
    rmse_position: float  # RMSE in meters
    mae_position: float  # MAE in meters
    rmse_altitude: float  # RMSE in meters
    mae_altitude: float  # MAE in meters
    rmse_velocity: float  # RMSE in m/s
    mae_velocity: float  # MAE in m/s
    num_samples: int


@dataclass
class CovarianceAnalysis:
    """Results of covariance convergence analysis."""
    callsign: str
    initial_cov_lat: float
    final_cov_lat: float
    initial_cov_lon: float
    final_cov_lon: float
    initial_cov_alt: float
    final_cov_alt: float
    convergence_rate: float
    steady_state_reached: bool


class KalmanAnalysis:
    """
    Comprehensive analysis class for Kalman filter data.
    
    Provides analysis functions for:
    - Aircraft tracking analysis
    - Kalman filter performance
    - Statistical analysis
    - Temporal analysis
    - Configuration analysis
    """
    
    def __init__(self):
        """Initialize the analysis class."""
        pass
    
    # ========================================================================
    # DATA EXPLORATION FUNCTIONS
    # ========================================================================
    
    def get_basic_statistics(self, df: pd.DataFrame) -> Dict:
        """
        Calculate basic statistics for all numeric columns.
        
        Args:
            df: DataFrame to analyze
            
        Returns:
            Dictionary with statistics (count, mean, std, min, max, quartiles)
        """
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        
        stats_dict = {}
        for col in numeric_cols:
            col_data = df[col].dropna()
            if len(col_data) > 0:
                stats_dict[col] = {
                    'count': len(col_data),
                    'mean': float(col_data.mean()),
                    'std': float(col_data.std()),
                    'min': float(col_data.min()),
                    'max': float(col_data.max()),
                    '25%': float(col_data.quantile(0.25)),
                    '50%': float(col_data.quantile(0.50)),
                    '75%': float(col_data.quantile(0.75))
                }
        
        return stats_dict
    
    def get_unique_values(self, df: pd.DataFrame, columns: List[str]) -> Dict:
        """
        Get unique values and counts for categorical columns.
        
        Args:
            df: DataFrame to analyze
            columns: List of column names to analyze
            
        Returns:
            Dictionary mapping column names to value counts
        """
        result = {}
        for col in columns:
            if col in df.columns:
                value_counts = df[col].value_counts().to_dict()
                result[col] = {
                    'unique_count': len(value_counts),
                    'values': value_counts,
                    'top_10': dict(list(value_counts.items())[:10])
                }
        return result
    
    def identify_data_gaps(self, df: pd.DataFrame, timestamp_col: str = 'timestamp') -> Dict:
        """
        Identify data gaps and missing values.
        
        Args:
            df: DataFrame to analyze
            timestamp_col: Name of the timestamp column
            
        Returns:
            Dictionary with gap analysis results
        """
        if timestamp_col not in df.columns or len(df) == 0:
            return {}
        
        # Sort by timestamp
        df_sorted = df.sort_values(timestamp_col)
        
        # Calculate time differences between consecutive rows
        time_diffs = df_sorted[timestamp_col].diff().dropna()
        
        gap_analysis = {
            'total_records': len(df),
            'missing_values_per_column': df.isnull().sum().to_dict(),
            'total_missing_values': df.isnull().sum().sum(),
            'missing_percentage_per_column': (df.isnull().mean() * 100).round(2).to_dict(),
            'avg_time_between_records': float(time_diffs.mean()) if len(time_diffs) > 0 else 0,
            'std_time_between_records': float(time_diffs.std()) if len(time_diffs) > 0 else 0,
            'max_gap': float(time_diffs.max()) if len(time_diffs) > 0 else 0,
            'min_gap': float(time_diffs.min()) if len(time_diffs) > 0 else 0,
            'gaps_greater_than_1s': int((time_diffs > 1.0).sum()),
            'gaps_greater_than_5s': int((time_diffs > 5.0).sum()),
            'gaps_greater_than_10s': int((time_diffs > 10.0).sum()),
        }
        
        return gap_analysis
    
    def plot_data_availability(self, df: pd.DataFrame, timestamp_col: str = 'timestamp') -> pd.DataFrame:
        """
        Prepare data for plotting data availability over time.
        
        Args:
            df: DataFrame to analyze
            timestamp_col: Name of the timestamp column
            
        Returns:
            DataFrame with resampled counts for plotting
        """
        if timestamp_col not in df.columns or len(df) == 0:
            return pd.DataFrame()
        
        df_copy = df.copy()
        df_copy['datetime'] = pd.to_datetime(df_copy[timestamp_col], unit='s')
        df_copy.set_index('datetime', inplace=True)
        
        # Resample by second and count
        availability = df_copy.resample('1S').size().reset_index(name='count')
        
        return availability
    
    # ========================================================================
    # AIRCRAFT TRACKING ANALYSIS
    # ========================================================================
    
    def get_aircraft_trajectories(self, predictions: pd.DataFrame) -> Dict[str, pd.DataFrame]:
        """
        Extract trajectories for individual aircraft from predictions.
        
        Args:
            predictions: Predictions DataFrame
            
        Returns:
            Dictionary mapping callsign to DataFrame of that aircraft's trajectory
        """
        trajectories = {}
        
        for callsign in predictions['callsign'].unique():
            aircraft_data = predictions[predictions['callsign'] == callsign].copy()
            aircraft_data.sort_values('timestamp', inplace=True)
            trajectories[callsign] = aircraft_data
        
        return trajectories
    
    def calculate_track_continuity(self, trajectory: pd.DataFrame) -> TrackContinuityMetrics:
        """
        Calculate track continuity metrics for a single aircraft.
        
        Args:
            trajectory: DataFrame with aircraft trajectory data
            
        Returns:
            TrackContinuityMetrics object
        """
        if len(trajectory) < 2:
            return TrackContinuityMetrics(
                callsign=trajectory['callsign'].iloc[0] if len(trajectory) > 0 else "unknown",
                total_frames=len(trajectory),
                continuous_segments=1,
                max_gap_frames=0,
                avg_gap_frames=0,
                total_gap_time=0,
                track_coverage=1.0 if len(trajectory) > 0 else 0
            )
        
        # Sort by frame_index
        trajectory = trajectory.sort_values('frame_index')
        
        # Calculate frame gaps
        frame_diffs = trajectory['frame_index'].diff().dropna()
        
        # Calculate time gaps
        time_diffs = trajectory['timestamp'].diff().dropna()
        
        # Identify continuous segments (gap of 1 frame = continuous)
        gaps = frame_diffs[frame_diffs > 1]
        
        # Count continuous segments
        continuous_segments = len(gaps) + 1
        
        # Calculate gap statistics
        max_gap = int(gaps.max()) if len(gaps) > 0 else 0
        avg_gap = float(gaps.mean()) if len(gaps) > 0 else 0
        total_gap_time = float(time_diffs[frame_diffs > 1].sum()) if len(gaps) > 0 else 0
        
        # Calculate track coverage (percentage of frames tracked)
        total_span = trajectory['frame_index'].max() - trajectory['frame_index'].min() + 1
        track_coverage = len(trajectory) / total_span if total_span > 0 else 1.0
        
        return TrackContinuityMetrics(
            callsign=trajectory['callsign'].iloc[0],
            total_frames=len(trajectory),
            continuous_segments=continuous_segments,
            max_gap_frames=max_gap,
            avg_gap_frames=avg_gap,
            total_gap_time=total_gap_time,
            track_coverage=track_coverage
        )
    
    def analyze_track_accuracy(
        self,
        predictions: pd.DataFrame,
        opensky: pd.DataFrame
    ) -> Dict[str, Dict]:
        """
        Analyze track accuracy by comparing predictions vs OpenSky data.
        
        Args:
            predictions: Predictions DataFrame
            opensky: OpenSky data DataFrame
            
        Returns:
            Dictionary mapping callsign to accuracy metrics
        """
        accuracy_metrics = {}
        
        # Get unique callsigns that appear in both datasets
        common_callsigns = set(predictions['callsign'].unique()) & set(opensky['callsign'].unique())
        
        for callsign in common_callsigns:
            # Get matching data for this callsign
            pred_data = predictions[predictions['callsign'] == callsign]
            os_data = opensky[opensky['callsign'] == callsign]
            
            # Find matching timestamps (approximate match within 1 second)
            matches = self._find_matching_timestamps(pred_data, os_data)
            
            if len(matches) > 0:
                errors = self._calculate_position_errors(matches['pred'], matches['os'])
                accuracy_metrics[callsign] = errors
        
        return accuracy_metrics
    
    def _find_matching_timestamps(
        self,
        pred_data: pd.DataFrame,
        os_data: pd.DataFrame,
        tolerance: float = 1.0
    ) -> Dict[str, pd.DataFrame]:
        """
        Find matching timestamps between predictions and OpenSky data.
        
        Args:
            pred_data: Predictions DataFrame for a single aircraft
            os_data: OpenSky DataFrame for the same aircraft
            tolerance: Maximum time difference in seconds
            
        Returns:
            Dictionary with 'pred' and 'os' DataFrames containing matched data
        """
        if len(pred_data) == 0 or len(os_data) == 0:
            return {'pred': pd.DataFrame(), 'os': pd.DataFrame()}
        
        # Sort both by timestamp
        pred_sorted = pred_data.sort_values('timestamp').reset_index(drop=True)
        os_sorted = os_data.sort_values('timestamp').reset_index(drop=True)
        
        matched_pred = []
        matched_os = []
        
        i, j = 0, 0
        while i < len(pred_sorted) and j < len(os_sorted):
            pred_time = pred_sorted.iloc[i]['timestamp']
            os_time = os_sorted.iloc[j]['timestamp']
            
            diff = abs(pred_time - os_time)
            
            if diff <= tolerance:
                # Found a match
                matched_pred.append(pred_sorted.iloc[i])
                matched_os.append(os_sorted.iloc[j])
                i += 1
                j += 1
            elif pred_time < os_time:
                i += 1
            else:
                j += 1
        
        return {
            'pred': pd.DataFrame(matched_pred),
            'os': pd.DataFrame(matched_os)
        }
    
    def _calculate_position_errors(
        self,
        pred_data: pd.DataFrame,
        os_data: pd.DataFrame
    ) -> Dict:
        """
        Calculate position errors between predictions and actual data.
        
        Args:
            pred_data: Predictions DataFrame
            os_data: OpenSky DataFrame
            
        Returns:
            Dictionary with error metrics
        """
        if len(pred_data) == 0 or len(os_data) == 0:
            return {}
        
        # Calculate distance between predicted and actual positions
        # Using haversine distance for lat/lon
        distances = []
        altitude_errors = []
        velocity_errors = []
        
        for i in range(len(pred_data)):
            pred = pred_data.iloc[i]
            actual = os_data.iloc[i]
            
            # Calculate distance in meters
            dist = self._haversine_distance(
                pred['latitude'], pred['longitude'],
                actual['latitude'], actual['longitude']
            )
            distances.append(dist)
            
            # Altitude error
            alt_error = abs(pred['baro_altitude'] - actual['baro_altitude'])
            altitude_errors.append(alt_error)
            
            # Velocity error
            vel_error = abs(pred['velocity'] - actual['velocity'])
            velocity_errors.append(vel_error)
        
        return {
            'num_samples': len(distances),
            'position_errors_m': distances,
            'altitude_errors_m': altitude_errors,
            'velocity_errors_knots': velocity_errors,
            'rmse_position': float(np.sqrt(np.mean(np.array(distances)**2))),
            'mae_position': float(np.mean(distances)),
            'rmse_altitude': float(np.sqrt(np.mean(np.array(altitude_errors)**2))),
            'mae_altitude': float(np.mean(altitude_errors)),
            'rmse_velocity': float(np.sqrt(np.mean(np.array(velocity_errors)**2))),
            'mae_velocity': float(np.mean(velocity_errors))
        }
    
    def _haversine_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Calculate haversine distance between two points in meters.
        
        Args:
            lat1, lon1: First point in degrees
            lat2, lon2: Second point in degrees
            
        Returns:
            Distance in meters
        """
        # Convert to radians
        lat1_rad = math.radians(lat1)
        lon1_rad = math.radians(lon1)
        lat2_rad = math.radians(lat2)
        lon2_rad = math.radians(lon2)
        
        # Haversine formula
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad
        
        a = math.sin(dlat / 2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        distance = EARTH_RADIUS * c
        return distance
    
    # ========================================================================
    # KALMAN FILTER PERFORMANCE ANALYSIS
    # ========================================================================
    
    def analyze_covariance_convergence(
        self,
        trajectory: pd.DataFrame
    ) -> CovarianceAnalysis:
        """
        Analyze covariance convergence for a tracked aircraft.
        
        Args:
            trajectory: DataFrame with aircraft trajectory data
            
        Returns:
            CovarianceAnalysis object
        """
        if len(trajectory) < 2:
            return CovarianceAnalysis(
                callsign=trajectory['callsign'].iloc[0] if len(trajectory) > 0 else "unknown",
                initial_cov_lat=0,
                final_cov_lat=0,
                initial_cov_lon=0,
                final_cov_lon=0,
                initial_cov_alt=0,
                final_cov_alt=0,
                convergence_rate=0,
                steady_state_reached=False
            )
        
        # Sort by timestamp
        trajectory = trajectory.sort_values('timestamp')
        
        # Get covariance values
        cov_lat = trajectory['covariance_lat'].dropna().values
        cov_lon = trajectory['covariance_lon'].dropna().values
        cov_alt = trajectory['covariance_alt'].dropna().values
        
        if len(cov_lat) < 2 or len(cov_lon) < 2 or len(cov_alt) < 2:
            return CovarianceAnalysis(
                callsign=trajectory['callsign'].iloc[0],
                initial_cov_lat=float(cov_lat[0]) if len(cov_lat) > 0 else 0,
                final_cov_lat=float(cov_lat[-1]) if len(cov_lat) > 0 else 0,
                initial_cov_lon=float(cov_lon[0]) if len(cov_lon) > 0 else 0,
                final_cov_lon=float(cov_lon[-1]) if len(cov_lon) > 0 else 0,
                initial_cov_alt=float(cov_alt[0]) if len(cov_alt) > 0 else 0,
                final_cov_alt=float(cov_alt[-1]) if len(cov_alt) > 0 else 0,
                convergence_rate=0,
                steady_state_reached=False
            )
        
        # Calculate convergence (reduction in covariance)
        initial_lat = cov_lat[0]
        final_lat = cov_lat[-1]
        initial_lon = cov_lon[0]
        final_lon = cov_lon[-1]
        initial_alt = cov_alt[0]
        final_alt = cov_alt[-1]
        
        # Calculate average convergence rate
        convergence_lat = (initial_lat - final_lat) / initial_lat if initial_lat > 0 else 0
        convergence_lon = (initial_lon - final_lon) / initial_lon if initial_lon > 0 else 0
        convergence_alt = (initial_alt - final_alt) / initial_alt if initial_alt > 0 else 0
        convergence_rate = (convergence_lat + convergence_lon + convergence_alt) / 3
        
        # Check if steady state reached (covariance stabilized)
        # Use the last 10% of data to check if variance is low
        window_size = max(10, len(cov_lat) // 10)
        recent_lat = cov_lat[-window_size:]
        recent_lon = cov_lon[-window_size:]
        recent_alt = cov_alt[-window_size:]
        
        std_lat = np.std(recent_lat) / np.mean(recent_lat) if np.mean(recent_lat) > 0 else 0
        std_lon = np.std(recent_lon) / np.mean(recent_lon) if np.mean(recent_lon) > 0 else 0
        std_alt = np.std(recent_alt) / np.mean(recent_alt) if np.mean(recent_alt) > 0 else 0
        
        avg_std = (std_lat + std_lon + std_alt) / 3
        steady_state_reached = avg_std < 0.1  # Less than 10% variation
        
        return CovarianceAnalysis(
            callsign=trajectory['callsign'].iloc[0],
            initial_cov_lat=float(initial_lat),
            final_cov_lat=float(final_lat),
            initial_cov_lon=float(initial_lon),
            final_cov_lon=float(final_lon),
            initial_cov_alt=float(initial_alt),
            final_cov_alt=float(final_alt),
            convergence_rate=float(convergence_rate),
            steady_state_reached=steady_state_reached
        )
    
    def analyze_state_transitions(self, predictions: pd.DataFrame) -> Dict:
        """
        Analyze state transitions (tracking -> coasting -> lost).
        
        Args:
            predictions: Predictions DataFrame
            
        Returns:
            Dictionary with state transition analysis
        """
        if 'state' not in predictions.columns or len(predictions) == 0:
            return {}
        
        # Sort by callsign and timestamp
        predictions = predictions.sort_values(['callsign', 'timestamp'])
        
        transition_counts = {}
        state_durations = {}
        
        for callsign in predictions['callsign'].unique():
            aircraft_data = predictions[predictions['callsign'] == callsign]
            
            if len(aircraft_data) < 2:
                continue
            
            # Get state transitions
            states = aircraft_data['state'].values
            timestamps = aircraft_data['timestamp'].values
            
            for i in range(1, len(states)):
                prev_state = states[i-1]
                curr_state = states[i]
                transition = f"{prev_state}->{curr_state}"
                
                if transition not in transition_counts:
                    transition_counts[transition] = 0
                transition_counts[transition] += 1
                
                # Calculate duration in each state
                time_diff = timestamps[i] - timestamps[i-1]
                if prev_state not in state_durations:
                    state_durations[prev_state] = 0
                state_durations[prev_state] += time_diff
            
            # Add duration for last state
            last_state = states[-1]
            if last_state not in state_durations:
                state_durations[last_state] = 0
        
        return {
            'transition_counts': transition_counts,
            'state_durations': state_durations,
            'state_transition_matrix': self._build_transition_matrix(predictions)
        }
    
    def _build_transition_matrix(self, predictions: pd.DataFrame) -> pd.DataFrame:
        """
        Build a state transition matrix.
        
        Args:
            predictions: Predictions DataFrame
            
        Returns:
            DataFrame with transition counts between states
        """
        if 'state' not in predictions.columns or len(predictions) == 0:
            return pd.DataFrame()
        
        # Get all unique states
        states = predictions['state'].unique()
        
        # Create transition matrix
        matrix = pd.DataFrame(0, index=states, columns=states)
        
        # Sort by callsign and timestamp
        predictions = predictions.sort_values(['callsign', 'timestamp'])
        
        for callsign in predictions['callsign'].unique():
            aircraft_data = predictions[predictions['callsign'] == callsign]
            
            if len(aircraft_data) < 2:
                continue
            
            state_seq = aircraft_data['state'].values
            
            for i in range(1, len(state_seq)):
                from_state = state_seq[i-1]
                to_state = state_seq[i]
                matrix.loc[from_state, to_state] += 1
        
        return matrix
    
    def calculate_prediction_error_statistics(
        self,
        predictions: pd.DataFrame,
        opensky: pd.DataFrame
    ) -> Dict:
        """
        Calculate overall prediction error statistics (RMSE, MAE).
        
        Args:
            predictions: Predictions DataFrame
            opensky: OpenSky DataFrame
            
        Returns:
            Dictionary with error statistics
        """
        # Get all matching pairs
        all_position_errors = []
        all_altitude_errors = []
        all_velocity_errors = []
        
        common_callsigns = set(predictions['callsign'].unique()) & set(opensky['callsign'].unique())
        
        for callsign in common_callsigns:
            pred_data = predictions[predictions['callsign'] == callsign]
            os_data = opensky[opensky['callsign'] == callsign]
            
            matches = self._find_matching_timestamps(pred_data, os_data)
            
            if len(matches['pred']) > 0:
                for i in range(len(matches['pred'])):
                    pred = matches['pred'].iloc[i]
                    actual = matches['os'].iloc[i]
                    
                    # Position error
                    dist = self._haversine_distance(
                        pred['latitude'], pred['longitude'],
                        actual['latitude'], actual['longitude']
                    )
                    all_position_errors.append(dist)
                    
                    # Altitude error
                    alt_error = abs(pred['baro_altitude'] - actual['baro_altitude'])
                    all_altitude_errors.append(alt_error)
                    
                    # Velocity error
                    vel_error = abs(pred['velocity'] - actual['velocity'])
                    all_velocity_errors.append(vel_error)
        
        if len(all_position_errors) == 0:
            return {}
        
        return {
            'num_samples': len(all_position_errors),
            'rmse_position_m': float(np.sqrt(np.mean(np.array(all_position_errors)**2))),
            'mae_position_m': float(np.mean(all_position_errors)),
            'std_position_m': float(np.std(all_position_errors)),
            'rmse_altitude_m': float(np.sqrt(np.mean(np.array(all_altitude_errors)**2))),
            'mae_altitude_m': float(np.mean(all_altitude_errors)),
            'std_altitude_m': float(np.std(all_altitude_errors)),
            'rmse_velocity_knots': float(np.sqrt(np.mean(np.array(all_velocity_errors)**2))),
            'mae_velocity_knots': float(np.mean(all_velocity_errors)),
            'std_velocity_knots': float(np.std(all_velocity_errors)),
            'max_position_error_m': float(np.max(all_position_errors)),
            'max_altitude_error_m': float(np.max(all_altitude_errors)),
            'max_velocity_error_knots': float(np.max(all_velocity_errors))
        }
    
    def analyze_velocity_vector_accuracy(
        self,
        predictions: pd.DataFrame,
        opensky: pd.DataFrame
    ) -> Dict:
        """
        Analyze velocity vector accuracy (v_north, v_east).
        
        Args:
            predictions: Predictions DataFrame
            opensky: OpenSky DataFrame
            
        Returns:
            Dictionary with velocity vector error metrics
        """
        all_v_north_errors = []
        all_v_east_errors = []
        
        common_callsigns = set(predictions['callsign'].unique()) & set(opensky['callsign'].unique())
        
        for callsign in common_callsigns:
            pred_data = predictions[predictions['callsign'] == callsign]
            os_data = opensky[opensky['callsign'] == callsign]
            
            matches = self._find_matching_timestamps(pred_data, os_data)
            
            if len(matches['pred']) > 0:
                for i in range(len(matches['pred'])):
                    pred = matches['pred'].iloc[i]
                    actual = matches['os'].iloc[i]
                    
                    v_north_error = abs(pred['v_north'] - actual['v_north'])
                    v_east_error = abs(pred['v_east'] - actual['v_east'])
                    
                    all_v_north_errors.append(v_north_error)
                    all_v_east_errors.append(v_east_error)
        
        if len(all_v_north_errors) == 0:
            return {}
        
        return {
            'num_samples': len(all_v_north_errors),
            'v_north_rmse': float(np.sqrt(np.mean(np.array(all_v_north_errors)**2))),
            'v_north_mae': float(np.mean(all_v_north_errors)),
            'v_north_std': float(np.std(all_v_north_errors)),
            'v_east_rmse': float(np.sqrt(np.mean(np.array(all_v_east_errors)**2))),
            'v_east_mae': float(np.mean(all_v_east_errors)),
            'v_east_std': float(np.std(all_v_east_errors)),
            'velocity_vector_rmse': float(np.sqrt(
                (np.mean(np.array(all_v_north_errors)**2) + np.mean(np.array(all_v_east_errors)**2)) / 2
            ))
        }
    
    # ========================================================================
    # STATISTICAL ANALYSIS
    # ========================================================================
    
    def analyze_aircraft_count(self, statistics: pd.DataFrame) -> pd.DataFrame:
        """
        Analyze aircraft count over time.
        
        Args:
            statistics: Statistics DataFrame
            
        Returns:
            DataFrame with resampled aircraft count for plotting
        """
        if len(statistics) == 0 or 'track_count' not in statistics.columns:
            return pd.DataFrame()
        
        df = statistics.copy()
        df['datetime'] = pd.to_datetime(df['timestamp'], unit='s')
        df.set_index('datetime', inplace=True)
        
        # Resample by second and take mean
        counts = df['track_count'].resample('1S').mean().reset_index()
        
        return counts
    
    def analyze_prediction_measurement_rates(self, statistics: pd.DataFrame) -> Dict:
        """
        Analyze prediction and measurement rates.
        
        Args:
            statistics: Statistics DataFrame
            
        Returns:
            Dictionary with rate analysis
        """
        if len(statistics) == 0:
            return {}
        
        # Calculate rates
        df = statistics.copy()
        df['datetime'] = pd.to_datetime(df['timestamp'], unit='s')
        df = df.sort_values('datetime')
        
        # Calculate time differences
        time_diffs = df['timestamp'].diff().dropna()
        
        if len(time_diffs) == 0:
            return {}
        
        prediction_diffs = df['prediction_count'].diff().dropna()
        measurement_diffs = df['total_measurements'].diff().dropna()
        
        return {
            'avg_time_between_frames': float(time_diffs.mean()),
            'std_time_between_frames': float(time_diffs.std()),
            'avg_predictions_per_frame': float(prediction_diffs.mean()),
            'std_predictions_per_frame': float(prediction_diffs.std()),
            'avg_measurements_per_frame': float(measurement_diffs.mean()) if len(measurement_diffs) > 0 else 0,
            'std_measurements_per_frame': float(measurement_diffs.std()) if len(measurement_diffs) > 0 else 0,
            'total_predictions': int(df['prediction_count'].sum()),
            'total_measurements': int(df['total_measurements'].max() if len(df) > 0 else 0)
        }
    
    def calculate_track_stability_metrics(self, predictions: pd.DataFrame) -> Dict:
        """
        Calculate track stability metrics.
        
        Args:
            predictions: Predictions DataFrame
            
        Returns:
            Dictionary with stability metrics
        """
        if len(predictions) == 0:
            return {}
        
        # Calculate position jumps between consecutive predictions
        predictions = predictions.sort_values(['callsign', 'timestamp'])
        
        position_jumps = []
        velocity_jumps = []
        altitude_jumps = []
        
        for callsign in predictions['callsign'].unique():
            aircraft_data = predictions[predictions['callsign'] == callsign]
            
            if len(aircraft_data) < 2:
                continue
            
            for i in range(1, len(aircraft_data)):
                prev = aircraft_data.iloc[i-1]
                curr = aircraft_data.iloc[i]
                
                # Position jump (meters)
                dist = self._haversine_distance(
                    prev['latitude'], prev['longitude'],
                    curr['latitude'], curr['longitude']
                )
                position_jumps.append(dist)
                
                # Velocity jump
                vel_jump = abs(curr['velocity'] - prev['velocity'])
                velocity_jumps.append(vel_jump)
                
                # Altitude jump
                alt_jump = abs(curr['baro_altitude'] - prev['baro_altitude'])
                altitude_jumps.append(alt_jump)
        
        if len(position_jumps) == 0:
            return {}
        
        return {
            'num_jumps': len(position_jumps),
            'avg_position_jump_m': float(np.mean(position_jumps)),
            'std_position_jump_m': float(np.std(position_jumps)),
            'max_position_jump_m': float(np.max(position_jumps)),
            'avg_velocity_jump_knots': float(np.mean(velocity_jumps)),
            'std_velocity_jump_knots': float(np.std(velocity_jumps)),
            'max_velocity_jump_knots': float(np.max(velocity_jumps)),
            'avg_altitude_jump_m': float(np.mean(altitude_jumps)),
            'std_altitude_jump_m': float(np.std(altitude_jumps)),
            'max_altitude_jump_m': float(np.max(altitude_jumps)),
            'large_jumps_count': int(sum(1 for x in position_jumps if x > 1000))  # > 1km jumps
        }
    
    def identify_anomalous_tracks(self, predictions: pd.DataFrame, threshold: float = 3.0) -> pd.DataFrame:
        """
        Identify anomalous tracks based on covariance and position jumps.
        
        Args:
            predictions: Predictions DataFrame
            threshold: Standard deviation threshold for anomaly detection
            
        Returns:
            DataFrame with anomalous records
        """
        if len(predictions) == 0:
            return pd.DataFrame()
        
        # Calculate position jumps
        predictions = predictions.sort_values(['callsign', 'timestamp'])
        
        position_jumps = []
        for callsign in predictions['callsign'].unique():
            aircraft_data = predictions[predictions['callsign'] == callsign]
            
            if len(aircraft_data) < 2:
                continue
            
            jumps = []
            for i in range(1, len(aircraft_data)):
                prev = aircraft_data.iloc[i-1]
                curr = aircraft_data.iloc[i]
                
                dist = self._haversine_distance(
                    prev['latitude'], prev['longitude'],
                    curr['latitude'], curr['longitude']
                )
                jumps.append(dist)
            
            # Extend jumps array to match data length
            jumps = [0] + jumps
            position_jumps.extend(jumps[:len(aircraft_data)])
        
        predictions = predictions.reset_index(drop=True)
        predictions['position_jump'] = position_jumps
        
        # Calculate z-scores for position jumps
        if len(position_jumps) > 0:
            mean_jump = np.mean(position_jumps)
            std_jump = np.std(position_jumps)
            predictions['jump_z_score'] = predictions['position_jump'].apply(
                lambda x: (x - mean_jump) / std_jump if std_jump > 0 else 0
            )
        
        # Identify anomalies (high covariance OR large jumps)
        is_anomalous = (
            (predictions['covariance_lat'] > predictions['covariance_lat'].quantile(0.95)) |
            (predictions['covariance_lon'] > predictions['covariance_lon'].quantile(0.95)) |
            (predictions['covariance_alt'] > predictions['covariance_alt'].quantile(0.95)) |
            (predictions['jump_z_score'] > threshold)
        )
        
        return predictions[is_anomalous]
    
    def analyze_altitude_distribution(self, predictions: pd.DataFrame) -> Dict:
        """
        Analyze altitude distribution and changes.
        
        Args:
            predictions: Predictions DataFrame
            
        Returns:
            Dictionary with altitude analysis
        """
        if len(predictions) == 0 or 'baro_altitude' not in predictions.columns:
            return {}
        
        altitudes = predictions['baro_altitude'].dropna()
        
        # Calculate altitude changes
        predictions = predictions.sort_values(['callsign', 'timestamp'])
        altitude_changes = []
        
        for callsign in predictions['callsign'].unique():
            aircraft_data = predictions[predictions['callsign'] == callsign]
            
            if len(aircraft_data) < 2:
                continue
            
            for i in range(1, len(aircraft_data)):
                change = aircraft_data.iloc[i]['baro_altitude'] - aircraft_data.iloc[i-1]['baro_altitude']
                altitude_changes.append(change)
        
        return {
            'num_samples': len(altitudes),
            'mean_altitude_m': float(altitudes.mean()),
            'std_altitude_m': float(altitudes.std()),
            'min_altitude_m': float(altitudes.min()),
            'max_altitude_m': float(altitudes.max()),
            'median_altitude_m': float(altitudes.median()),
            'altitude_bins': self._create_altitude_bins(altitudes),
            'mean_altitude_change_m': float(np.mean(altitude_changes)) if len(altitude_changes) > 0 else 0,
            'std_altitude_change_m': float(np.std(altitude_changes)) if len(altitude_changes) > 0 else 0,
            'max_climb_rate_mps': float(np.max(altitude_changes)) if len(altitude_changes) > 0 else 0,
            'max_descent_rate_mps': float(np.min(altitude_changes)) if len(altitude_changes) > 0 else 0
        }
    
    def _create_altitude_bins(self, altitudes: pd.Series, bin_size: int = 1000) -> Dict:
        """
        Create altitude distribution bins.
        
        Args:
            altitudes: Series of altitude values
            bin_size: Size of altitude bins in meters
            
        Returns:
            Dictionary with altitude bin counts
        """
        if len(altitudes) == 0:
            return {}
        
        min_alt = int(altitudes.min() // bin_size) * bin_size
        max_alt = int(altitudes.max() // bin_size + 1) * bin_size
        
        bins = range(min_alt, max_alt + bin_size, bin_size)
        counts, bin_edges = np.histogram(altitudes, bins=bins)
        
        return {
            f"{int(bin_edges[i])}-{int(bin_edges[i+1])}m": int(counts[i])
            for i in range(len(counts))
        }
    
    # ========================================================================
    # TEMPORAL ANALYSIS
    # ========================================================================
    
    def analyze_update_intervals(self, statistics: pd.DataFrame) -> Dict:
        """
        Analyze data update intervals.
        
        Args:
            statistics: Statistics DataFrame
            
        Returns:
            Dictionary with interval analysis
        """
        if len(statistics) == 0 or 'timestamp' not in statistics.columns:
            return {}
        
        statistics = statistics.sort_values('timestamp')
        time_diffs = statistics['timestamp'].diff().dropna()
        
        if len(time_diffs) == 0:
            return {}
        
        return {
            'num_intervals': len(time_diffs),
            'mean_interval_s': float(time_diffs.mean()),
            'std_interval_s': float(time_diffs.std()),
            'min_interval_s': float(time_diffs.min()),
            'max_interval_s': float(time_diffs.max()),
            'median_interval_s': float(time_diffs.median()),
            'interval_histogram': self._create_histogram(time_diffs, bins=20),
            'intervals_greater_than_1s': int((time_diffs > 1.0).sum()),
            'intervals_greater_than_2s': int((time_diffs > 2.0).sum()),
            'intervals_greater_than_5s': int((time_diffs > 5.0).sum()),
        }
    
    def analyze_frame_timing_consistency(self, statistics: pd.DataFrame) -> Dict:
        """
        Analyze frame timing consistency.
        
        Args:
            statistics: Statistics DataFrame
            
        Returns:
            Dictionary with timing consistency analysis
        """
        if len(statistics) == 0:
            return {}
        
        statistics = statistics.sort_values('timestamp')
        
        # Calculate expected interval (mean of all intervals)
        time_diffs = statistics['timestamp'].diff().dropna()
        
        if len(time_diffs) == 0:
            return {}
        
        expected_interval = time_diffs.mean()
        
        # Calculate deviation from expected
        deviations = time_diffs - expected_interval
        
        return {
            'expected_interval_s': float(expected_interval),
            'mean_deviation_s': float(deviations.mean()),
            'std_deviation_s': float(deviations.std()),
            'max_positive_deviation_s': float(deviations.max()),
            'max_negative_deviation_s': float(deviations.min()),
            'jitter_coefficient': float(deviations.std() / expected_interval) if expected_interval > 0 else 0
        }
    
    def identify_timing_anomalies(self, statistics: pd.DataFrame, threshold: float = 2.0) -> pd.DataFrame:
        """
        Identify timing anomalies or delays.
        
        Args:
            statistics: Statistics DataFrame
            threshold: Standard deviation threshold for anomaly detection
            
        Returns:
            DataFrame with anomalous timing records
        """
        if len(statistics) < 2:
            return pd.DataFrame()
        
        statistics = statistics.sort_values('timestamp')
        time_diffs = statistics['timestamp'].diff()
        
        mean_diff = time_diffs.mean()
        std_diff = time_diffs.std()
        
        # Identify anomalies
        statistics['time_diff'] = time_diffs
        statistics['z_score'] = (statistics['time_diff'] - mean_diff) / std_diff if std_diff > 0 else 0
        
        is_anomalous = abs(statistics['z_score']) > threshold
        
        return statistics[is_anomalous]
    
    def correlate_timing_with_prediction_quality(
        self,
        statistics: pd.DataFrame,
        predictions: pd.DataFrame
    ) -> Dict:
        """
        Correlate timing with prediction quality.
        
        Args:
            statistics: Statistics DataFrame
            predictions: Predictions DataFrame
            
        Returns:
            Dictionary with correlation analysis
        """
        if len(statistics) == 0 or len(predictions) == 0:
            return {}
        
        # Merge statistics with predictions
        # For each prediction, find the corresponding statistics frame
        predictions = predictions.sort_values('timestamp')
        statistics = statistics.sort_values('timestamp')
        
        # Find closest statistics for each prediction
        merged = pd.merge_asof(
            predictions,
            statistics,
            on='timestamp',
            direction='nearest',
            tolerance=pd.Timedelta(seconds=1)
        )
        
        if len(merged) == 0:
            return {}
        
        # Calculate correlation between timing and covariance
        # Use the time since last update as a measure
        if 'timestamp' in merged.columns and 'covariance_lat' in merged.columns:
            # Calculate time differences between predictions
            merged = merged.sort_values(['callsign', 'timestamp'])
            
            correlations = {}
            
            for callsign in merged['callsign'].unique():
                aircraft_data = merged[merged['callsign'] == callsign]
                
                if len(aircraft_data) < 2:
                    continue
                
                # Calculate time since last prediction
                time_since_last = aircraft_data['timestamp'].diff().fillna(0)
                
                # Correlate with covariance
                corr_lat = aircraft_data['covariance_lat'].corr(time_since_last)
                corr_lon = aircraft_data['covariance_lon'].corr(time_since_last)
                corr_alt = aircraft_data['covariance_alt'].corr(time_since_last)
                
                correlations[callsign] = {
                    'cov_lat_corr': float(corr_lat),
                    'cov_lon_corr': float(corr_lon),
                    'cov_alt_corr': float(corr_alt),
                    'avg_corr': float((corr_lat + corr_lon + corr_alt) / 3)
                }
            
            return {
                'correlations': correlations,
                'overall_avg_correlation': float(np.mean([
                    v['avg_corr'] for v in correlations.values()
                ])) if correlations else 0
            }
        
        return {}
    
    def _create_histogram(self, data: pd.Series, bins: int = 10) -> Dict:
        """
        Create histogram data.
        
        Args:
            data: Series of numeric data
            bins: Number of bins
            
        Returns:
            Dictionary with histogram data
        """
        if len(data) == 0:
            return {}
        
        counts, bin_edges = np.histogram(data, bins=bins)
        
        return {
            'bin_edges': [float(x) for x in bin_edges],
            'counts': [int(x) for x in counts]
        }
    
    # ========================================================================
    # CONFIGURATION ANALYSIS
    # ========================================================================
    
    def compare_configurations(self, metadata_list: List[Dict]) -> Dict:
        """
        Compare performance across different Kalman configurations.
        
        Args:
            metadata_list: List of session metadata with kalman_config
            
        Returns:
            Dictionary with configuration comparison
        """
        if not metadata_list:
            return {}
        
        configs = {}
        
        for metadata in metadata_list:
            config = metadata.kalman_config
            config_key = (
                config.get('position_process_noise', 0),
                config.get('velocity_process_noise', 0),
                config.get('position_measurement_noise', 0),
                config.get('data_update_interval', 0),
                config.get('prediction_interval', 0)
            )
            
            if config_key not in configs:
                configs[config_key] = {
                    'position_process_noise': config.get('position_process_noise', 0),
                    'velocity_process_noise': config.get('velocity_process_noise', 0),
                    'position_measurement_noise': config.get('position_measurement_noise', 0),
                    'data_update_interval': config.get('data_update_interval', 0),
                    'prediction_interval': config.get('prediction_interval', 0),
                    'session_count': 0,
                    'total_predictions': 0,
                    'total_measurements': 0,
                    'max_track_count': 0
                }
            
            configs[config_key]['session_count'] += 1
        
        # Sort configs by session count
        sorted_configs = sorted(configs.items(), key=lambda x: x[1]['session_count'], reverse=True)
        
        return {
            'configurations': [v for _, v in sorted_configs],
            'unique_configs': len(configs)
        }
    
    def analyze_process_noise_impact(self, predictions: pd.DataFrame, metadata_list: List[Dict]) -> Dict:
        """
        Analyze impact of process noise parameters on performance.
        
        Args:
            predictions: Predictions DataFrame
            metadata_list: List of session metadata
            
        Returns:
            Dictionary with process noise analysis
        """
        # Group predictions by process noise values
        noise_to_data = {}
        
        for metadata in metadata_list:
            session_id = metadata.session_id
            process_noise = metadata.kalman_config.get('position_process_noise', 0)
            
            if process_noise not in noise_to_data:
                noise_to_data[process_noise] = []
            
            # Add session data
            session_preds = predictions[predictions['session_id'] == session_id]
            if len(session_preds) > 0:
                noise_to_data[process_noise].append(session_preds)
        
        # Calculate metrics for each noise level
        noise_metrics = {}
        
        for noise, data_list in noise_to_data.items():
            all_data = pd.concat(data_list, ignore_index=True)
            
            # Calculate average covariance
            avg_cov_lat = all_data['covariance_lat'].mean()
            avg_cov_lon = all_data['covariance_lon'].mean()
            avg_cov_alt = all_data['covariance_alt'].mean()
            
            noise_metrics[noise] = {
                'avg_covariance_lat': float(avg_cov_lat),
                'avg_covariance_lon': float(avg_cov_lon),
                'avg_covariance_alt': float(avg_cov_alt),
                'num_predictions': len(all_data),
                'num_sessions': len(data_list)
            }
        
        return {
            'noise_levels': list(noise_metrics.keys()),
            'metrics': noise_metrics
        }
    
    def analyze_measurement_noise_impact(self, predictions: pd.DataFrame, metadata_list: List[Dict]) -> Dict:
        """
        Analyze impact of measurement noise parameters on performance.
        
        Args:
            predictions: Predictions DataFrame
            metadata_list: List of session metadata
            
        Returns:
            Dictionary with measurement noise analysis
        """
        # Group predictions by measurement noise values
        noise_to_data = {}
        
        for metadata in metadata_list:
            session_id = metadata.session_id
            measurement_noise = metadata.kalman_config.get('position_measurement_noise', 0)
            
            if measurement_noise not in noise_to_data:
                noise_to_data[measurement_noise] = []
            
            # Add session data
            session_preds = predictions[predictions['session_id'] == session_id]
            if len(session_preds) > 0:
                noise_to_data[measurement_noise].append(session_preds)
        
        # Calculate metrics for each noise level
        noise_metrics = {}
        
        for noise, data_list in noise_to_data.items():
            all_data = pd.concat(data_list, ignore_index=True)
            
            # Calculate convergence rate
            convergence_rates = []
            for callsign in all_data['callsign'].unique():
                trajectory = all_data[all_data['callsign'] == callsign]
                if len(trajectory) >= 2:
                    cov_analysis = self.analyze_covariance_convergence(trajectory)
                    convergence_rates.append(cov_analysis.convergence_rate)
            
            avg_convergence = np.mean(convergence_rates) if convergence_rates else 0
            
            noise_metrics[noise] = {
                'avg_convergence_rate': float(avg_convergence),
                'num_steady_state_tracks': int(sum(
                    self.analyze_covariance_convergence(
                        all_data[all_data['callsign'] == cs]
                    ).steady_state_reached
                    for cs in all_data['callsign'].unique()
                )),
                'num_predictions': len(all_data),
                'num_sessions': len(data_list)
            }
        
        return {
            'measurement_noise_levels': list(noise_metrics.keys()),
            'metrics': noise_metrics
        }
    
    def evaluate_update_interval_effects(self, predictions: pd.DataFrame, metadata_list: List[Dict]) -> Dict:
        """
        Evaluate effects of update interval on performance.
        
        Args:
            predictions: Predictions DataFrame
            metadata_list: List of session metadata
            
        Returns:
            Dictionary with update interval analysis
        """
        # Group by update interval
        interval_to_data = {}
        
        for metadata in metadata_list:
            session_id = metadata.session_id
            update_interval = metadata.kalman_config.get('data_update_interval', 0)
            
            if update_interval not in interval_to_data:
                interval_to_data[update_interval] = []
            
            session_preds = predictions[predictions['session_id'] == session_id]
            if len(session_preds) > 0:
                interval_to_data[update_interval].append(session_preds)
        
        # Calculate metrics for each interval
        interval_metrics = {}
        
        for interval, data_list in interval_to_data.items():
            all_data = pd.concat(data_list, ignore_index=True)
            
            # Calculate track continuity
            avg_coverage = []
            for callsign in all_data['callsign'].unique():
                trajectory = all_data[all_data['callsign'] == callsign]
                if len(trajectory) >= 2:
                    metrics = self.calculate_track_continuity(trajectory)
                    avg_coverage.append(metrics.track_coverage)
            
            interval_metrics[interval] = {
                'avg_track_coverage': float(np.mean(avg_coverage)) if avg_coverage else 0,
                'num_predictions': len(all_data),
                'num_sessions': len(data_list),
                'num_unique_aircraft': all_data['callsign'].nunique()
            }
        
        return {
            'update_intervals': list(interval_metrics.keys()),
            'metrics': interval_metrics
        }
    
    def generate_configuration_recommendations(
        self,
        predictions: pd.DataFrame,
        opensky: pd.DataFrame,
        metadata_list: List[Dict]
    ) -> Dict:
        """
        Generate Kalman filter configuration recommendations.
        
        Args:
            predictions: Predictions DataFrame
            opensky: OpenSky DataFrame
            metadata_list: List of session metadata
            
        Returns:
            Dictionary with configuration recommendations
        """
        recommendations = {}
        
        # Calculate overall error statistics
        error_stats = self.calculate_prediction_error_statistics(predictions, opensky)
        
        if error_stats:
            # Position error recommendations
            if error_stats['rmse_position_m'] > 1000:
                recommendations['position_process_noise'] = \
                    "Increase position process noise to allow for more uncertainty in position changes"
            elif error_stats['rmse_position_m'] < 100:
                recommendations['position_process_noise'] = \
                    "Decrease position process noise for more stable position estimates"
            else:
                recommendations['position_process_noise'] = \
                    "Position process noise appears well-tuned"
            
            # Altitude error recommendations
            if error_stats['rmse_altitude_m'] > 500:
                recommendations['altitude_process_noise'] = \
                    "Increase altitude process noise or check vertical rate measurement accuracy"
            elif error_stats['rmse_altitude_m'] < 50:
                recommendations['altitude_process_noise'] = \
                    "Altitude tracking is performing well"
            else:
                recommendations['altitude_process_noise'] = \
                    "Altitude process noise appears adequate"
            
            # Velocity error recommendations
            if error_stats['rmse_velocity_knots'] > 50:
                recommendations['velocity_process_noise'] = \
                    "Increase velocity process noise to account for acceleration"
            elif error_stats['rmse_velocity_knots'] < 10:
                recommendations['velocity_process_noise'] = \
                    "Velocity tracking is performing well"
            else:
                recommendations['velocity_process_noise'] = \
                    "Velocity process noise appears adequate"
        
        # Measurement noise recommendations
        covariance_stats = self.analyze_process_noise_impact(predictions, metadata_list)
        if covariance_stats:
            avg_cov = np.mean([
                v['avg_covariance_lat'] + v['avg_covariance_lon'] + v['avg_covariance_alt']
                for v in covariance_stats['metrics'].values()
            ]) / 3
            
            if avg_cov > 100:
                recommendations['measurement_noise'] = \
                    "Increase measurement noise to account for higher measurement uncertainty"
            elif avg_cov < 10:
                recommendations['measurement_noise'] = \
                    "Decrease measurement noise for more confident measurements"
            else:
                recommendations['measurement_noise'] = \
                    "Measurement noise appears well-tuned"
        
        # Update interval recommendations
        timing_stats = self.analyze_frame_timing_consistency(self._get_mock_statistics(predictions))
        if timing_stats and timing_stats.get('jitter_coefficient', 0) > 0.5:
            recommendations['update_interval'] = \
                "Increase update interval or improve timing consistency for better predictions"
        
        return {
            'recommendations': recommendations,
            'priority': self._prioritize_recommendations(recommendations),
            'current_configs': [m.kalman_config for m in metadata_list]
        }
    
    def _get_mock_statistics(self, predictions: pd.DataFrame) -> pd.DataFrame:
        """Create mock statistics DataFrame for analysis when statistics.csv is empty."""
        if len(predictions) == 0:
            return pd.DataFrame()
        
        # Group by timestamp and count
        stats = predictions.groupby('timestamp').agg({
            'callsign': 'count',
            'frame_index': 'first'
        }).reset_index()
        
        stats.rename(columns={'callsign': 'track_count'}, inplace=True)
        stats['prediction_count'] = stats['track_count']
        stats['total_predictions'] = stats['track_count'].cumsum()
        stats['total_measurements'] = stats['track_count'].cumsum()
        stats['session_id'] = predictions['session_id'].iloc[0]
        
        return stats
    
    def _prioritize_recommendations(self, recommendations: Dict) -> Dict:
        """Prioritize recommendations based on impact."""
        priority_map = {
            'position_process_noise': 'HIGH',
            'altitude_process_noise': 'HIGH',
            'velocity_process_noise': 'MEDIUM',
            'measurement_noise': 'HIGH',
            'update_interval': 'MEDIUM'
        }
        
        return {
            k: priority_map.get(k, 'LOW')
            for k, v in recommendations.items()
        }


# Create a global instance for convenience
kalman_analysis = KalmanAnalysis()
