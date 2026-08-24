"""
Data Loading Module for Kalman Filter Analysis

This module provides functions to load and parse captured aircraft tracking
and Kalman filter prediction data from the TURRET system's CSV storage backend.

Author: TURRET Analysis System
Version: 1.0.0
"""

import os
import json
import glob
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
from dataclasses import dataclass
import pandas as pd
import numpy as np


@dataclass
class SessionMetadata:
    """Container for session metadata from metadata.json."""
    capture_start: float
    capture_end: Optional[float]
    session_id: str
    turret_version: str
    file_format_version: str
    format_type: str
    kalman_config: Dict
    location: Dict


@dataclass
class SessionData:
    """Container for all data from a single capture session."""
    metadata: SessionMetadata
    predictions: pd.DataFrame
    opensky_data: pd.DataFrame
    statistics: pd.DataFrame
    session_path: str


class DataLoader:
    """
    Loads and parses captured data from TURRET's CSV storage backend.
    
    Provides functions to:
    - Load data from CSV files (predictions, opensky_data, statistics)
    - Parse metadata.json for session configuration
    - Handle multiple session directories
    - Support loading data from a specific date or date range
    - Provide summary statistics of loaded data
    """
    
    # Column schemas for validation
    PREDICTIONS_COLUMNS = [
        'timestamp', 'frame_index', 'session_id', 'callsign',
        'latitude', 'longitude', 'baro_altitude', 'velocity',
        'true_track', 'vertical_rate', 'covariance_lat',
        'covariance_lon', 'covariance_alt', 'state', 'v_north', 'v_east'
    ]
    
    OPENSKY_COLUMNS = [
        'timestamp', 'frame_index', 'session_id', 'callsign',
        'latitude', 'longitude', 'baro_altitude', 'velocity',
        'true_track', 'vertical_rate', 'on_ground', 'v_north', 'v_east'
    ]
    
    STATISTICS_COLUMNS = [
        'timestamp', 'frame_index', 'session_id',
        'track_count', 'prediction_count', 'total_predictions', 'total_measurements'
    ]
    
    def __init__(self, captures_dir: str = "captures"):
        """
        Initialize the DataLoader.
        
        Args:
            captures_dir: Path to the captures directory (relative or absolute)
        """
        self.captures_dir = Path(captures_dir)
        
    def _find_session_directories(self, date_str: Optional[str] = None) -> List[Path]:
        """
        Find all session directories in the captures directory.
        
        Args:
            date_str: Optional date string in YYYY-MM-DD format to filter by date
            
        Returns:
            List of Path objects pointing to session directories
        """
        session_dirs = []
        
        # Pattern for session directories: YYYY-MM-DD/HH-MM-SS_session_XXXX
        pattern = os.path.join(self.captures_dir, "*", "*_session_*")
        
        for path in glob.glob(pattern):
            if os.path.isdir(path):
                metadata_path = os.path.join(path, "metadata.json")
                if os.path.exists(metadata_path):
                    # Filter by date if specified
                    if date_str:
                        # Extract date from path (parent directory)
                        parent_dir = Path(path).parent.name
                        if parent_dir == date_str:
                            session_dirs.append(Path(path))
                    else:
                        session_dirs.append(Path(path))
        
        # Sort by path (newest first)
        session_dirs.sort(reverse=True)
        return session_dirs
    
    def _load_metadata(self, session_path: Path) -> SessionMetadata:
        """
        Load and parse metadata.json from a session directory.
        
        Args:
            session_path: Path to the session directory
            
        Returns:
            SessionMetadata object with parsed metadata
        """
        metadata_path = session_path / "metadata.json"
        
        with open(metadata_path, 'r') as f:
            metadata = json.load(f)
        
        return SessionMetadata(
            capture_start=metadata.get('capture_start', 0.0),
            capture_end=metadata.get('capture_end', None),
            session_id=metadata.get('session_id', 'unknown'),
            turret_version=metadata.get('turret_version', 'unknown'),
            file_format_version=metadata.get('file_format_version', 'unknown'),
            format_type=metadata.get('format', 'csv'),
            kalman_config=metadata.get('kalman_config', {}),
            location=metadata.get('location', {})
        )
    
    def _load_csv(self, file_path: Path, expected_columns: List[str]) -> pd.DataFrame:
        """
        Load a CSV file with validation.
        
        Args:
            file_path: Path to the CSV file
            expected_columns: List of expected column names
            
        Returns:
            pandas DataFrame with the CSV data
        """
        if not file_path.exists():
            # Return empty DataFrame with expected columns
            return pd.DataFrame(columns=expected_columns)
        
        try:
            df = pd.read_csv(file_path)
            
            # Validate columns
            missing_cols = [col for col in expected_columns if col not in df.columns]
            if missing_cols:
                print(f"Warning: Missing columns in {file_path.name}: {missing_cols}")
            
            # Ensure all expected columns exist
            for col in expected_columns:
                if col not in df.columns:
                    df[col] = np.nan
            
            # Reorder columns to match expected order
            df = df[expected_columns]
            
            return df
        except Exception as e:
            print(f"Error loading {file_path}: {e}")
            return pd.DataFrame(columns=expected_columns)
    
    def load_session(self, session_path: Union[str, Path]) -> Optional[SessionData]:
        """
        Load all data from a single session directory.
        
        Args:
            session_path: Path to the session directory
            
        Returns:
            SessionData object containing all loaded data, or None if error
        """
        session_path = Path(session_path)
        
        # Validate session directory
        if not session_path.exists():
            print(f"Session directory not found: {session_path}")
            return None
        
        metadata_path = session_path / "metadata.json"
        if not metadata_path.exists():
            print(f"Metadata file not found: {metadata_path}")
            return None
        
        try:
            # Load metadata
            metadata = self._load_metadata(session_path)
            
            # Load CSV files
            predictions_path = session_path / "predictions.csv"
            opensky_path = session_path / "opensky_data.csv"
            statistics_path = session_path / "statistics.csv"
            
            predictions = self._load_csv(predictions_path, self.PREDICTIONS_COLUMNS)
            opensky_data = self._load_csv(opensky_path, self.OPENSKY_COLUMNS)
            statistics = self._load_csv(statistics_path, self.STATISTICS_COLUMNS)
            
            return SessionData(
                metadata=metadata,
                predictions=predictions,
                opensky_data=opensky_data,
                statistics=statistics,
                session_path=str(session_path)
            )
        except Exception as e:
            print(f"Error loading session {session_path}: {e}")
            return None
    
    def load_sessions(
        self, 
        date_str: Optional[str] = None,
        limit: Optional[int] = None
    ) -> Dict[str, SessionData]:
        """
        Load data from multiple session directories.
        
        Args:
            date_str: Optional date string in YYYY-MM-DD format to filter by date
            limit: Maximum number of sessions to load (None for all)
            
        Returns:
            Dictionary mapping session_id to SessionData objects
        """
        session_dirs = self._find_session_directories(date_str)
        
        sessions = {}
        
        for session_path in session_dirs:
            if limit and len(sessions) >= limit:
                break
            
            session_data = self.load_session(session_path)
            if session_data:
                sessions[session_data.metadata.session_id] = session_data
        
        return sessions
    
    def load_all_data(
        self,
        date_str: Optional[str] = None,
        limit: Optional[int] = None
    ) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, List[SessionMetadata]]:
        """
        Load and merge data from all matching sessions.
        
        Args:
            date_str: Optional date string in YYYY-MM-DD format to filter by date
            limit: Maximum number of sessions to load (None for all)
            
        Returns:
            Tuple of (predictions_df, opensky_df, statistics_df, metadata_list)
        """
        sessions = self.load_sessions(date_str, limit)
        
        if not sessions:
            return (
                pd.DataFrame(columns=self.PREDICTIONS_COLUMNS),
                pd.DataFrame(columns=self.OPENSKY_COLUMNS),
                pd.DataFrame(columns=self.STATISTICS_COLUMNS),
                []
            )
        
        # Concatenate all data
        all_predictions = []
        all_opensky = []
        all_statistics = []
        all_metadata = []
        
        for session_id, session_data in sessions.items():
            all_predictions.append(session_data.predictions)
            all_opensky.append(session_data.opensky_data)
            all_statistics.append(session_data.statistics)
            all_metadata.append(session_data.metadata)
        
        predictions_df = pd.concat(all_predictions, ignore_index=True) if all_predictions else pd.DataFrame(columns=self.PREDICTIONS_COLUMNS)
        opensky_df = pd.concat(all_opensky, ignore_index=True) if all_opensky else pd.DataFrame(columns=self.OPENSKY_COLUMNS)
        statistics_df = pd.concat(all_statistics, ignore_index=True) if all_statistics else pd.DataFrame(columns=self.STATISTICS_COLUMNS)
        
        return predictions_df, opensky_df, statistics_df, all_metadata
    
    def get_session_summary(self, session_data: SessionData) -> Dict:
        """
        Generate summary statistics for a session.
        
        Args:
            session_data: SessionData object
            
        Returns:
            Dictionary with summary statistics
        """
        summary = {
            'session_id': session_data.metadata.session_id,
            'session_path': session_data.session_path,
            'capture_start': session_data.metadata.capture_start,
            'capture_end': session_data.metadata.capture_end,
            'kalman_config': session_data.metadata.kalman_config,
            'location': session_data.metadata.location,
            
            # Predictions summary
            'num_predictions': len(session_data.predictions),
            'num_unique_callsigns_predictions': session_data.predictions['callsign'].nunique() if not session_data.predictions.empty else 0,
            'prediction_states': session_data.predictions['state'].value_counts().to_dict() if not session_data.predictions.empty else {},
            
            # OpenSky data summary
            'num_opensky_records': len(session_data.opensky_data),
            'num_unique_callsigns_opensky': session_data.opensky_data['callsign'].nunique() if not session_data.opensky_data.empty else 0,
            'num_on_ground': session_data.opensky_data['on_ground'].sum() if not session_data.opensky_data.empty else 0,
            
            # Statistics summary
            'num_statistics_records': len(session_data.statistics),
            'total_predictions': session_data.statistics['total_predictions'].max() if not session_data.statistics.empty else 0,
            'total_measurements': session_data.statistics['total_measurements'].max() if not session_data.statistics.empty else 0,
            'max_track_count': session_data.statistics['track_count'].max() if not session_data.statistics.empty else 0,
            
            # Time range
            'prediction_time_range': (
                session_data.predictions['timestamp'].min(),
                session_data.predictions['timestamp'].max()
            ) if not session_data.predictions.empty else (None, None),
            
            'opensky_time_range': (
                session_data.opensky_data['timestamp'].min(),
                session_data.opensky_data['timestamp'].max()
            ) if not session_data.opensky_data.empty else (None, None),
        }
        
        return summary
    
    def get_combined_summary(
        self,
        predictions: pd.DataFrame,
        opensky: pd.DataFrame,
        statistics: pd.DataFrame,
        metadata_list: List[SessionMetadata]
    ) -> Dict:
        """
        Generate combined summary statistics for all loaded data.
        
        Args:
            predictions: Combined predictions DataFrame
            opensky: Combined OpenSky data DataFrame
            statistics: Combined statistics DataFrame
            metadata_list: List of SessionMetadata objects
            
        Returns:
            Dictionary with combined summary statistics
        """
        summary = {
            'num_sessions': len(metadata_list),
            
            # Time ranges
            'predictions_time_range': (
                predictions['timestamp'].min(),
                predictions['timestamp'].max()
            ) if not predictions.empty else (None, None),
            
            'opensky_time_range': (
                opensky['timestamp'].min(),
                opensky['timestamp'].max()
            ) if not opensky.empty else (None, None),
            
            # Data counts
            'total_predictions': len(predictions),
            'total_opensky_records': len(opensky),
            'total_statistics_records': len(statistics),
            
            # Unique identifiers
            'unique_callsigns_predictions': predictions['callsign'].nunique() if not predictions.empty else 0,
            'unique_callsigns_opensky': opensky['callsign'].nunique() if not opensky.empty else 0,
            'unique_sessions': predictions['session_id'].nunique() if not predictions.empty else 0,
            
            # Kalman filter states
            'state_distribution': predictions['state'].value_counts().to_dict() if not predictions.empty else {},
            
            # Data quality
            'predictions_missing_values': predictions.isnull().sum().to_dict() if not predictions.empty else {},
            'opensky_missing_values': opensky.isnull().sum().to_dict() if not opensky.empty else {},
            
            # Statistics aggregates
            'total_predictions_all': statistics['total_predictions'].max() if not statistics.empty else 0,
            'total_measurements_all': statistics['total_measurements'].max() if not statistics.empty else 0,
            'max_track_count': statistics['track_count'].max() if not statistics.empty else 0,
            'avg_track_count': statistics['track_count'].mean() if not statistics.empty else 0,
            
            # Kalman configurations
            'kalman_configs': [m.kalman_config for m in metadata_list],
            
            # Location data
            'capture_locations': [m.location for m in metadata_list],
        }
        
        return summary
    
    def find_available_dates(self) -> List[str]:
        """
        Find all available dates in the captures directory.
        
        Returns:
            List of date strings in YYYY-MM-DD format
        """
        dates = []
        date_pattern = os.path.join(self.captures_dir, "[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]")
        
        for path in glob.glob(date_pattern):
            if os.path.isdir(path):
                dates.append(os.path.basename(path))
        
        dates.sort(reverse=True)
        return dates
    
    def find_sessions_for_date(self, date_str: str) -> List[str]:
        """
        Find all session directories for a specific date.
        
        Args:
            date_str: Date string in YYYY-MM-DD format
            
        Returns:
            List of session directory paths
        """
        sessions = []
        session_pattern = os.path.join(self.captures_dir, date_str, "*_session_*")
        
        for path in glob.glob(session_pattern):
            if os.path.isdir(path):
                metadata_path = os.path.join(path, "metadata.json")
                if os.path.exists(metadata_path):
                    sessions.append(path)
        
        sessions.sort(reverse=True)
        return sessions


def create_data_loader(captures_dir: str = "captures") -> DataLoader:
    """
    Factory function to create a DataLoader instance.
    
    Args:
        captures_dir: Path to the captures directory
        
    Returns:
        DataLoader instance
    """
    return DataLoader(captures_dir)


# Convenience functions for direct use in notebooks
def load_session_data(session_path: str) -> Optional[SessionData]:
    """Load data from a single session directory."""
    loader = DataLoader()
    return loader.load_session(session_path)


def load_all_sessions(captures_dir: str = "captures", date_str: Optional[str] = None) -> Tuple:
    """Load all data from all sessions."""
    loader = DataLoader(captures_dir)
    return loader.load_all_data(date_str)


def get_available_dates(captures_dir: str = "captures") -> List[str]:
    """Get list of available dates with capture data."""
    loader = DataLoader(captures_dir)
    return loader.find_available_dates()
