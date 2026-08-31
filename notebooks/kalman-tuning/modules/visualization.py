"""
Visualization Module for Kalman Filter Analysis

This module provides reusable plotting functions for visualizing TURRET
captured data and Kalman filter analysis results.

Author: TURRET Analysis System
Version: 1.0.0
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Dict, List, Optional, Tuple, Any
from matplotlib.figure import Figure
from matplotlib.axes import Axes
import warnings


# Suppress matplotlib warnings for cleaner output
warnings.filterwarnings('ignore', category=UserWarning, module='matplotlib')


class KalmanVisualizer:
    """
    Comprehensive visualization class for Kalman filter data analysis.
    
    Provides plotting functions for:
    - Interactive aircraft trajectory plots
    - Time-series plots for key metrics
    - Histograms for distributions
    - Scatter plots for correlations
    - Heatmaps for spatial density
    - 3D plots for altitude analysis
    - Kalman filter performance plots (covariance, errors, state transitions)
    """
    
    def __init__(self, figsize: Tuple[int, int] = (12, 8), dpi: int = 100):
        """
        Initialize the visualizer with default figure settings.
        
        Args:
            figsize: Default figure size (width, height)
            dpi: Default DPI for figures
        """
        self.figsize = figsize
        self.dpi = dpi
        
        # Set default style
        self._set_default_style()
    
    def _set_default_style(self) -> None:
        """Set default matplotlib and seaborn styles."""
        plt.style.use('seaborn-v0_8')
        sns.set_palette("husl")
        plt.rcParams['figure.figsize'] = self.figsize
        plt.rcParams['figure.dpi'] = self.dpi
        plt.rcParams['font.size'] = 12
        plt.rcParams['axes.labelsize'] = 14
        plt.rcParams['axes.titlesize'] = 16
        plt.rcParams['legend.fontsize'] = 12
        plt.rcParams['xtick.labelsize'] = 12
        plt.rcParams['ytick.labelsize'] = 12
    
    # ========================================================================
    # AIRCRAFT TRAJECTORY VISUALIZATION
    # ========================================================================
    
    def plot_aircraft_trajectories(
        self,
        predictions: pd.DataFrame,
        callsigns: Optional[List[str]] = None,
        show_covariance: bool = False,
        figsize: Optional[Tuple[int, int]] = None,
        ax: Optional[Axes] = None,
        **kwargs
    ) -> Tuple[Figure, Axes]:
        """
        Plot aircraft trajectories on a 2D map (latitude vs longitude).
        
        Args:
            predictions: Predictions DataFrame
            callsigns: List of specific callsigns to plot (None for all)
            show_covariance: Whether to show covariance as error bars
            figsize: Custom figure size
            ax: Existing axes to plot on
            **kwargs: Additional keyword arguments for scatter plot
            
        Returns:
            Tuple of (figure, axes) objects
        """
        if figsize is None:
            figsize = (14, 10)
        
        # Filter by callsigns if specified
        if callsigns:
            predictions = predictions[predictions['callsign'].isin(callsigns)]
        
        if len(predictions) == 0:
            fig, ax = plt.subplots(figsize=figsize)
            ax.set_title("No Aircraft Trajectory Data")
            return fig, ax
        
        # Create figure
        if ax is None:
            fig, ax = plt.subplots(figsize=figsize)
        else:
            fig = ax.get_figure()
        
        # Plot trajectories
        unique_callsigns = predictions['callsign'].unique()
        colors = sns.color_palette("husl", n_colors=len(unique_callsigns))
        
        for i, callsign in enumerate(unique_callsigns):
            aircraft_data = predictions[predictions['callsign'] == callsign].sort_values('timestamp')
            
            # Plot trajectory line
            ax.plot(
                aircraft_data['longitude'],
                aircraft_data['latitude'],
                marker='o',
                markersize=3,
                linewidth=1.5,
                label=callsign,
                color=colors[i],
                alpha=0.7,
                **kwargs
            )
            
            # Add start point marker
            if len(aircraft_data) > 0:
                ax.scatter(
                    aircraft_data.iloc[0]['longitude'],
                    aircraft_data.iloc[0]['latitude'],
                    marker='>',
                    s=100,
                    color=colors[i],
                    label=f"{callsign} Start"
                )
        
        ax.set_xlabel("Longitude (degrees)")
        ax.set_ylabel("Latitude (degrees)")
        ax.set_title("Aircraft Trajectories" + (f" - {len(unique_callsigns)} Aircraft" if callsigns is None else ""))
        ax.grid(True, alpha=0.3)
        ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
        
        return fig, ax
    
    def plot_interactive_trajectory_map(
        self,
        trajectory: pd.DataFrame,
        callsign: str = "Unknown",
        show_velocity: bool = True,
        figsize: Optional[Tuple[int, int]] = None
    ) -> Tuple[Figure, Axes]:
        """
        Create an interactive-style trajectory plot with velocity vectors.
        
        Args:
            trajectory: DataFrame with trajectory data for a single aircraft
            callsign: Aircraft callsign
            show_velocity: Whether to show velocity vectors
            figsize: Custom figure size
            
        Returns:
            Tuple of (figure, axes) objects
        """
        if figsize is None:
            figsize = (12, 8)
        
        if len(trajectory) == 0:
            fig, ax = plt.subplots(figsize=figsize)
            ax.set_title(f"No Data for {callsign}")
            return fig, ax
        
        fig, ax = plt.subplots(figsize=figsize)
        
        # Plot trajectory
        ax.plot(
            trajectory['longitude'],
            trajectory['latitude'],
            'b-',
            linewidth=2,
            alpha=0.6,
            label='Trajectory'
        )
        
        # Add points
        ax.scatter(
            trajectory['longitude'],
            trajectory['latitude'],
            c=trajectory['timestamp'],
            cmap='viridis',
            s=50,
            alpha=0.6,
            label='Predictions'
        )
        
        # Add velocity vectors
        if show_velocity and 'v_north' in trajectory.columns and 'v_east' in trajectory.columns:
            # Sample every n points for clarity
            n = max(1, len(trajectory) // 20)
            
            for i in range(0, len(trajectory), n):
                row = trajectory.iloc[i]
                
                # Convert v_north, v_east to lon/lat deltas (approximate)
                # For visualization, we'll use a simple approximation
                lat = row['latitude']
                lon = row['longitude']
                v_north = row['v_north']
                v_east = row['v_east']
                
                # Approximate conversion (1 degree lat ~ 111km)
                delta_lat = v_north / 111000.0
                delta_lon = v_east / (111000.0 * abs(np.cos(np.radians(lat))))
                
                ax.arrow(
                    lon, lat,
                    delta_lon * 10,  # Scale for visibility
                    delta_lat * 10,
                    head_width=0.0005,
                    head_length=0.001,
                    fc='red',
                    ec='red',
                    alpha=0.5,
                    length_includes_head=True
                )
        
        # Add start and end markers
        if len(trajectory) > 0:
            ax.scatter(
                [trajectory.iloc[0]['longitude']],
                [trajectory.iloc[0]['latitude']],
                marker='>',
                s=200,
                color='green',
                label='Start',
                zorder=10
            )
            ax.scatter(
                [trajectory.iloc[-1]['longitude']],
                [trajectory.iloc[-1]['latitude']],
                marker='<',
                s=200,
                color='red',
                label='End',
                zorder=10
            )
        
        ax.set_xlabel("Longitude (degrees)")
        ax.set_ylabel("Latitude (degrees)")
        ax.set_title(f"Aircraft Trajectory: {callsign}")
        ax.grid(True, alpha=0.3)
        ax.legend()
        
        return fig, ax
    
    def plot_3d_trajectory(
        self,
        trajectory: pd.DataFrame,
        callsign: str = "Unknown",
        figsize: Optional[Tuple[int, int]] = None
    ) -> Figure:
        """
        Create a 3D plot for altitude analysis.
        
        Args:
            trajectory: DataFrame with trajectory data
            callsign: Aircraft callsign
            figsize: Custom figure size
            
        Returns:
            Figure object with 3D axes
        """
        from mpl_toolkits.mplot3d import Axes3D
        
        if figsize is None:
            figsize = (12, 8)
        
        if len(trajectory) == 0:
            fig = plt.figure(figsize=figsize)
            fig.suptitle(f"No Data for 3D Trajectory: {callsign}")
            return fig
        
        fig = plt.figure(figsize=figsize)
        ax = fig.add_subplot(111, projection='3d')
        
        # Plot trajectory
        ax.plot(
            trajectory['longitude'],
            trajectory['latitude'],
            trajectory['baro_altitude'] / 1000,  # Convert to km
            'b-',
            linewidth=2,
            alpha=0.6
        )
        
        # Add points colored by time
        scatter = ax.scatter(
            trajectory['longitude'],
            trajectory['latitude'],
            trajectory['baro_altitude'] / 1000,
            c=trajectory['timestamp'],
            cmap='viridis',
            s=30,
            alpha=0.6
        )
        
        # Add colorbar
        cbar = fig.colorbar(scatter, ax=ax, pad=0.1)
        cbar.set_label('Timestamp')
        
        ax.set_xlabel("Longitude (degrees)")
        ax.set_ylabel("Latitude (degrees)")
        ax.set_zlabel("Altitude (km)")
        ax.set_title(f"3D Trajectory: {callsign}")
        
        return fig
    
    def plot_3d_trajectory_interactive(
        self,
        predictions: pd.DataFrame,
        measurements: pd.DataFrame,
        callsign: str = "Unknown",
        width: int = 900,
        height: int = 700
    ) -> Any:
        """
        Create an interactive 3D plot for altitude analysis using Plotly.
        
        This creates a fully interactive 3D visualization that can be rotated,
        zoomed, and panned in the notebook.
        
        Args:
            trajectory: DataFrame with trajectory data
            callsign: Aircraft callsign
            width: Figure width in pixels
            height: Figure height in pixels
            
        Returns:
            Plotly Figure object (or None if Plotly not available)
        """
        try:
            import plotly.graph_objects as go
            import plotly.express as px
        except ImportError:
            print("Plotly not available. Install with: pip install plotly")
            return None
        
        if len(predictions) == 0:
            print(f"No data for interactive 3D trajectory: {callsign}")
            return None
        
        # Create figure
        fig = go.Figure()

        # Get unique timestamps from measurements (max 20 as per user)
        measurement_timestamps = measurements['timestamp'].unique()
        num_timestamps = len(measurement_timestamps)
        
        # Create discrete colormap for timestamps
        # Use qualitative color maps with distinct colors for up to 20 timestamps
        if num_timestamps <= 10:
            colormap = px.colors.qualitative.Plotly[:num_timestamps]
        elif num_timestamps <= 20:
            # Use first num_timestamps from Dark24 (which has 24 colors)
            colormap = px.colors.qualitative.Dark24[:num_timestamps]
        else:
            # Fallback to sequential for more than 20
            # Sample colors from Viridis colorscale
            import plotly.colors as pc
            colormap = pc.sample_colorscale('Viridis', num_timestamps)
        
        # Create color mapping: timestamp -> color
        timestamp_colors = {}
        for i, ts in enumerate(measurement_timestamps):
            timestamp_colors[ts] = colormap[i]
        
        # For measurements: map each point to its timestamp's color
        measurement_colors = [timestamp_colors[ts] for ts in measurements['timestamp']]
        
        # Add measurements as line with colored segments
        measurements_sorted = measurements.sort_values('timestamp')
        fig.add_trace(go.Scatter3d(
            x=measurements_sorted['longitude'],
            y=measurements_sorted['latitude'],
            z=measurements_sorted['baro_altitude'] / 1000,
            mode='lines+markers',
            line=dict(
                color=measurement_colors,
                width=4
            ),
            marker=dict(
                size=4,
                color=measurement_colors
            ),
            name='Measurements'
        ))
        
        # For predictions: associate each with its measurement timestamp
        # Match predictions to measurements by timestamp (nearest match)
        prediction_colors = []
        for pred_ts in predictions['timestamp']:
            # Find closest measurement timestamp
            time_diffs = abs(measurement_timestamps - pred_ts)
            closest_idx = time_diffs.argmin()
            closest_ts = measurement_timestamps[closest_idx]
            prediction_colors.append(timestamp_colors[closest_ts])
        
        # Add predictions as markers with matching measurement colors
        fig.add_trace(go.Scatter3d(
            x=predictions['longitude'],
            y=predictions['latitude'],
            z=predictions['baro_altitude'] / 1000,
            mode='markers',
            marker=dict(
                size=6,
                color=prediction_colors,
                opacity=0.8,
                line=dict(
                    width=1,
                    color='DarkSlateGrey'
                )
            ),
            name='Predictions'
        ))
        
        # Add start marker
        fig.add_trace(go.Scatter3d(
            x=[predictions.iloc[0]['longitude']],
            y=[predictions.iloc[0]['latitude']],
            z=[predictions.iloc[0]['baro_altitude'] / 1000],
            mode='markers',
            marker=dict(
                size=10,
                color='green',
                symbol='diamond'
            ),
            name='Start'
        ))
        
        # Add end marker
        fig.add_trace(go.Scatter3d(
            x=[predictions.iloc[-1]['longitude']],
            y=[predictions.iloc[-1]['latitude']],
            z=[predictions.iloc[-1]['baro_altitude'] / 1000],
            mode='markers',
            marker=dict(
                size=10,
                color='red',
                symbol='diamond'
            ),
            name='End'
        ))
        
        # Configure layout
        fig.update_layout(
            title=f'Interactive 3D Trajectory: {callsign}',
            scene=dict(
                xaxis_title='Longitude (degrees)',
                yaxis_title='Latitude (degrees)',
                zaxis_title='Altitude (km)',
                camera=dict(
                    eye=dict(x=1.5, y=1.5, z=1.3)
                )
            ),
            width=width,
            height=height,
            showlegend=True
        )
        
        return fig
    
    # ========================================================================
    # KALMAN FILTER PERFORMANCE VISUALIZATION
    # ========================================================================
    
    def plot_covariance_over_time(
        self,
        trajectory: pd.DataFrame,
        callsign: str = "Unknown",
        figsize: Optional[Tuple[int, int]] = None,
        ax: Optional[Axes] = None
    ) -> Tuple[Figure, Axes]:
        """
        Plot covariance values over time for each dimension (lat, lon, alt).
        
        Args:
            trajectory: DataFrame with trajectory data
            callsign: Aircraft callsign
            figsize: Custom figure size
            ax: Existing axes to plot on
            
        Returns:
            Tuple of (figure, axes) objects
        """
        if figsize is None:
            figsize = (12, 6)
        
        if len(trajectory) == 0:
            fig, ax = plt.subplots(figsize=figsize)
            ax.set_title(f"No Data for Covariance: {callsign}")
            return fig, ax
        
        if ax is None:
            fig, ax = plt.subplots(figsize=figsize)
        else:
            fig = ax.get_figure()
        
        # Convert timestamp to relative time for better visualization
        t0 = trajectory['timestamp'].min()
        trajectory['relative_time'] = trajectory['timestamp'] - t0
        
        # Plot covariance for each dimension
        if 'covariance_lat' in trajectory.columns:
            ax.plot(
                trajectory['relative_time'],
                trajectory['covariance_lat'],
                'r-',
                linewidth=2,
                label='Lat covariance',
                alpha=0.7
            )
        
        if 'covariance_lon' in trajectory.columns:
            ax.plot(
                trajectory['relative_time'],
                trajectory['covariance_lon'],
                'g-',
                linewidth=2,
                label='Lon covariance',
                alpha=0.7
            )
        
        if 'covariance_alt' in trajectory.columns:
            ax.plot(
                trajectory['relative_time'],
                trajectory['covariance_alt'],
                'b-',
                linewidth=2,
                label='Alt covariance',
                alpha=0.7
            )
        
        ax.set_xlabel("Time (s)")
        ax.set_ylabel("Covariance")
        ax.set_title(f"Covariance over Time: {callsign}")
        ax.grid(True, alpha=0.3)
        ax.legend()
        ax.set_yscale('log')  # Covariance often varies over orders of magnitude
        
        return fig, ax
    
    def plot_covariance_comparison(
        self,
        predictions: pd.DataFrame,
        callsigns: Optional[List[str]] = None,
        figsize: Optional[Tuple[int, int]] = None
    ) -> Tuple[Figure, Axes]:
        """
        Plot covariance comparison for multiple aircraft.
        
        Args:
            predictions: Predictions DataFrame
            callsigns: List of specific callsigns to plot (None for all)
            figsize: Custom figure size
            
        Returns:
            Tuple of (figure, axes) objects
        """
        if figsize is None:
            figsize = (12, 8)
        
        # Filter by callsigns if specified
        if callsigns:
            predictions = predictions[predictions['callsign'].isin(callsigns)]
        
        if len(predictions) == 0:
            fig, ax = plt.subplots(figsize=figsize)
            ax.set_title("No Data for Covariance Comparison")
            return fig, ax
        
        fig, axes = plt.subplots(3, 1, figsize=figsize, sharex=True)
        
        unique_callsigns = predictions['callsign'].unique()
        colors = sns.color_palette("husl", n_colors=len(unique_callsigns))
        
        for i, callsign in enumerate(unique_callsigns):
            aircraft_data = predictions[predictions['callsign'] == callsign].sort_values('timestamp')
            t0 = aircraft_data['timestamp'].min()
            aircraft_data['relative_time'] = aircraft_data['timestamp'] - t0
            
            # Plot on each subplot
            if 'covariance_lat' in aircraft_data.columns:
                axes[0].plot(
                    aircraft_data['relative_time'],
                    aircraft_data['covariance_lat'],
                    color=colors[i],
                    linewidth=1.5,
                    label=callsign,
                    alpha=0.7
                )
            
            if 'covariance_lon' in aircraft_data.columns:
                axes[1].plot(
                    aircraft_data['relative_time'],
                    aircraft_data['covariance_lon'],
                    color=colors[i],
                    linewidth=1.5,
                    label=callsign,
                    alpha=0.7
                )
            
            if 'covariance_alt' in aircraft_data.columns:
                axes[2].plot(
                    aircraft_data['relative_time'],
                    aircraft_data['covariance_alt'],
                    color=colors[i],
                    linewidth=1.5,
                    label=callsign,
                    alpha=0.7
                )
        
        # Configure subplots
        axes[0].set_ylabel("Lat Covariance")
        axes[1].set_ylabel("Lon Covariance")
        axes[2].set_ylabel("Alt Covariance")
        axes[2].set_xlabel("Time (s)")
        
        for ax in axes:
            ax.grid(True, alpha=0.3)
            ax.set_yscale('log')
            ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
        
        fig.suptitle("Covariance Comparison Across Aircraft")
        plt.tight_layout()
        
        return fig, axes[0]
    
    def plot_prediction_errors(
        self,
        error_data: Dict,
        figsize: Optional[Tuple[int, int]] = None
    ) -> Tuple[Figure, Axes]:
        """
        Plot prediction error statistics.
        
        Args:
            error_data: Dictionary with error metrics (from analyze_track_accuracy)
            figsize: Custom figure size
            
        Returns:
            Tuple of (figure, axes) objects
        """
        if figsize is None:
            figsize = (12, 8)
        
        if not error_data:
            fig, ax = plt.subplots(figsize=figsize)
            ax.set_title("No Error Data Available")
            return fig, ax
        
        fig, axes = plt.subplots(3, 1, figsize=figsize, sharex=True)
        
        # Collect all errors
        all_errors = {}
        for callsign, errors in error_data.items():
            if 'position_errors_m' in errors:
                all_errors[callsign] = errors
        
        if not all_errors:
            fig, ax = plt.subplots(figsize=figsize)
            ax.set_title("No Error Data Available")
            return fig, ax
        
        # Position errors
        for callsign, errors in all_errors.items():
            if 'position_errors_m' in errors and len(errors['position_errors_m']) > 0:
                axes[0].plot(
                    list(range(len(errors['position_errors_m']))),
                    errors['position_errors_m'],
                    'o-',
                    linewidth=1,
                    markersize=3,
                    label=callsign,
                    alpha=0.6
                )
        
        # Altitude errors
        for callsign, errors in all_errors.items():
            if 'altitude_errors_m' in errors and len(errors['altitude_errors_m']) > 0:
                axes[1].plot(
                    list(range(len(errors['altitude_errors_m']))),
                    errors['altitude_errors_m'],
                    'o-',
                    linewidth=1,
                    markersize=3,
                    label=callsign,
                    alpha=0.6
                )
        
        # Velocity errors
        for callsign, errors in all_errors.items():
            if 'velocity_errors_knots' in errors and len(errors['velocity_errors_knots']) > 0:
                axes[2].plot(
                    list(range(len(errors['velocity_errors_knots']))),
                    errors['velocity_errors_knots'],
                    'o-',
                    linewidth=1,
                    markersize=3,
                    label=callsign,
                    alpha=0.6
                )
        
        # Configure subplots
        axes[0].set_ylabel("Position Error (m)")
        axes[1].set_ylabel("Altitude Error (m)")
        axes[2].set_ylabel("Velocity Error (knots)")
        axes[2].set_xlabel("Sample Index")
        
        for ax in axes:
            ax.grid(True, alpha=0.3)
            ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
        
        fig.suptitle("Prediction Errors Over Time")
        plt.tight_layout()
        
        return fig, axes[0]
    
    def plot_state_transition_matrix(
        self,
        transition_matrix: pd.DataFrame,
        figsize: Optional[Tuple[int, int]] = None,
        ax: Optional[Axes] = None
    ) -> Tuple[Figure, Axes]:
        """
        Plot state transition matrix as a heatmap.
        
        Args:
            transition_matrix: DataFrame with state transition counts
            figsize: Custom figure size
            ax: Existing axes to plot on
            
        Returns:
            Tuple of (figure, axes) objects
        """
        if figsize is None:
            figsize = (8, 6)
        
        if transition_matrix.empty:
            fig, ax = plt.subplots(figsize=figsize)
            ax.set_title("No State Transition Data")
            return fig, ax
        
        if ax is None:
            fig, ax = plt.subplots(figsize=figsize)
        else:
            fig = ax.get_figure()
        
        sns.heatmap(
            transition_matrix,
            annot=True,
            fmt='d',
            cmap='Blues',
            ax=ax,
            cbar_kws={'label': 'Transition Count'}
        )
        
        ax.set_xlabel("To State")
        ax.set_ylabel("From State")
        ax.set_title("State Transition Matrix")
        
        return fig, ax
    
    # ========================================================================
    # STATISTICAL VISUALIZATION
    # ========================================================================
    
    def plot_aircraft_count(
        self,
        count_data: pd.DataFrame,
        figsize: Optional[Tuple[int, int]] = None,
        ax: Optional[Axes] = None
    ) -> Tuple[Figure, Axes]:
        """
        Plot aircraft count over time.
        
        Args:
            count_data: DataFrame with datetime and count columns
            figsize: Custom figure size
            ax: Existing axes to plot on
            
        Returns:
            Tuple of (figure, axes) objects
        """
        if figsize is None:
            figsize = (12, 6)
        
        if len(count_data) == 0 or 'count' not in count_data.columns:
            fig, ax = plt.subplots(figsize=figsize)
            ax.set_title("No Aircraft Count Data")
            return fig, ax
        
        if ax is None:
            fig, ax = plt.subplots(figsize=figsize)
        else:
            fig = ax.get_figure()
        
        ax.plot(count_data['datetime'], count_data['count'], 'b-', linewidth=2)
        ax.fill_between(count_data['datetime'], count_data['count'], alpha=0.3)
        
        ax.set_xlabel("Time")
        ax.set_ylabel("Aircraft Count")
        ax.set_title("Aircraft Count Over Time")
        ax.grid(True, alpha=0.3)
        
        # Rotate x-axis labels
        plt.setp(ax.get_xticklabels(), rotation=45, ha='right')
        
        return fig, ax
    
    def plot_distribution_histograms(
        self,
        data: pd.DataFrame,
        columns: List[str],
        figsize: Optional[Tuple[int, int]] = None,
        bins: int = 20
    ) -> Tuple[Figure, List[Axes]]:
        """
        Plot histograms for distributions of specified columns.
        
        Args:
            data: DataFrame with data
            columns: List of column names to plot
            figsize: Custom figure size
            bins: Number of bins
            
        Returns:
            Tuple of (figure, list of axes) objects
        """
        if figsize is None:
            figsize = (15, 10)
        
        if not columns:
            fig, ax = plt.subplots(figsize=figsize)
            ax.set_title("No Columns Specified")
            return fig, [ax]
        
        # Filter to only numeric columns
        numeric_cols = [col for col in columns if col in data.select_dtypes(include=[np.number]).columns]
        
        if not numeric_cols:
            fig, ax = plt.subplots(figsize=figsize)
            ax.set_title("No Numeric Columns to Plot")
            return fig, [ax]
        
        # Create subplots
        n_cols = min(3, len(numeric_cols))
        n_rows = (len(numeric_cols) + n_cols - 1) // n_cols
        
        fig, axes = plt.subplots(n_rows, n_cols, figsize=figsize)
        
        if n_rows == 1:
            axes = [axes] if n_cols == 1 else list(axes)
        else:
            axes = [ax for row in axes for ax in row]
        
        for i, col in enumerate(numeric_cols):
            if i >= len(axes):
                break
            
            axes[i].hist(data[col].dropna(), bins=bins, alpha=0.7, edgecolor='black')
            axes[i].set_xlabel(col)
            axes[i].set_ylabel("Frequency")
            axes[i].set_title(f"Distribution of {col}")
            axes[i].grid(True, alpha=0.3)
        
        # Hide unused subplots
        for i in range(len(numeric_cols), len(axes)):
            axes[i].axis('off')
        
        fig.suptitle("Data Distributions")
        plt.tight_layout()
        
        return fig, axes[:len(numeric_cols)]
    
    def plot_scatter_correlation(
        self,
        data: pd.DataFrame,
        x_col: str,
        y_col: str,
        hue_col: Optional[str] = None,
        figsize: Optional[Tuple[int, int]] = None,
        ax: Optional[Axes] = None,
        **kwargs
    ) -> Tuple[Figure, Axes]:
        """
        Create scatter plot for correlation analysis.
        
        Args:
            data: DataFrame with data
            x_col: Column for x-axis
            y_col: Column for y-axis
            hue_col: Column for color coding (optional)
            figsize: Custom figure size
            ax: Existing axes to plot on
            **kwargs: Additional keyword arguments for scatter plot
            
        Returns:
            Tuple of (figure, axes) objects
        """
        if figsize is None:
            figsize = (10, 8)
        
        if x_col not in data.columns or y_col not in data.columns:
            fig, ax = plt.subplots(figsize=figsize)
            ax.set_title(f"Columns Not Found: {x_col}, {y_col}")
            return fig, ax
        
        if ax is None:
            fig, ax = plt.subplots(figsize=figsize)
        else:
            fig = ax.get_figure()
        
        if hue_col and hue_col in data.columns:
            sns.scatterplot(
                data=data,
                x=x_col,
                y=y_col,
                hue=hue_col,
                palette="husl",
                ax=ax,
                **kwargs
            )
        else:
            ax.scatter(data[x_col], data[y_col], **kwargs)
        
        ax.set_xlabel(x_col)
        ax.set_ylabel(y_col)
        ax.set_title(f"{y_col} vs {x_col}")
        ax.grid(True, alpha=0.3)
        
        return fig, ax
    
    def plot_spatial_density_heatmap(
        self,
        predictions: pd.DataFrame,
        callsigns: Optional[List[str]] = None,
        bins: int = 50,
        figsize: Optional[Tuple[int, int]] = None,
        ax: Optional[Axes] = None
    ) -> Tuple[Figure, Axes]:
        """
        Create heatmap for spatial density of predictions.
        
        Args:
            predictions: Predictions DataFrame
            callsigns: List of specific callsigns to include (None for all)
            bins: Number of bins for heatmap
            figsize: Custom figure size
            ax: Existing axes to plot on
            
        Returns:
            Tuple of (figure, axes) objects
        """
        if figsize is None:
            figsize = (12, 10)
        
        # Filter by callsigns if specified
        if callsigns:
            predictions = predictions[predictions['callsign'].isin(callsigns)]
        
        if len(predictions) == 0:
            fig, ax = plt.subplots(figsize=figsize)
            ax.set_title("No Data for Spatial Density")
            return fig, ax
        
        if ax is None:
            fig, ax = plt.subplots(figsize=figsize)
        else:
            fig = ax.get_figure()
        
        # Create 2D histogram
        hb = ax.hexbin(
            predictions['longitude'],
            predictions['latitude'],
            gridsize=bins,
            cmap='Blues',
            bins='log',
            mincnt=1
        )
        
        cb = fig.colorbar(hb, ax=ax)
        cb.set_label('Log Count')
        
        ax.set_xlabel("Longitude (degrees)")
        ax.set_ylabel("Latitude (degrees)")
        ax.set_title("Spatial Density of Predictions")
        
        return fig, ax
    
    # ========================================================================
    # TEMPORAL ANALYSIS VISUALIZATION
    # ========================================================================
    
    def plot_update_intervals(
        self,
        interval_data: Dict,
        figsize: Optional[Tuple[int, int]] = None
    ) -> Tuple[Figure, Axes]:
        """
        Plot data update interval analysis.
        
        Args:
            interval_data: Dictionary with interval analysis data
            figsize: Custom figure size
            
        Returns:
            Tuple of (figure, axes) objects
        """
        if figsize is None:
            figsize = (12, 8)
        
        if not interval_data or 'interval_histogram' not in interval_data:
            fig, ax = plt.subplots(figsize=figsize)
            ax.set_title("No Interval Data Available")
            return fig, ax
        
        fig, axes = plt.subplots(2, 2, figsize=figsize)
        
        # Plot histogram
        hist_data = interval_data['interval_histogram']
        if hist_data:
            axes[0, 0].bar(
                hist_data['bin_edges'][:-1],
                hist_data['counts'],
                width=np.diff(hist_data['bin_edges']),
                alpha=0.7,
                edgecolor='black'
            )
            axes[0, 0].set_xlabel("Interval (s)")
            axes[0, 0].set_ylabel("Frequency")
            axes[0, 0].set_title("Interval Distribution")
            axes[0, 0].grid(True, alpha=0.3)
        
        # Plot statistics
        if 'mean_interval_s' in interval_data:
            stats_text = (
                f"Mean: {interval_data['mean_interval_s']:.3f}s\n"
                f"Std: {interval_data['std_interval_s']:.3f}s\n"
                f"Min: {interval_data['min_interval_s']:.3f}s\n"
                f"Max: {interval_data['max_interval_s']:.3f}s\n"
                f"Median: {interval_data['median_interval_s']:.3f}s"
            )
            axes[0, 1].text(
                0.1, 0.5, stats_text,
                fontsize=14,
                verticalalignment='center',
                transform=axes[0, 1].transAxes
            )
            axes[0, 1].set_title("Interval Statistics")
            axes[0, 1].axis('off')
        
        # Plot gaps greater than thresholds
        thresholds = [1, 2, 5]
        counts = [
            interval_data.get(f'intervals_greater_than_{t}s', 0)
            for t in thresholds
        ]
        
        if any(counts):
            axes[1, 0].bar(
                [f'>{t}s' for t in thresholds],
                counts,
                color=['orange', 'red', 'darkred'],
                alpha=0.7
            )
            axes[1, 0].set_ylabel("Count")
            axes[1, 0].set_title("Intervals Exceeding Thresholds")
            axes[1, 0].grid(True, alpha=0.3)
        
        axes[1, 1].axis('off')
        
        fig.suptitle("Update Interval Analysis")
        plt.tight_layout()
        
        return fig, axes[0, 0]
    
    def plot_timing_anomalies(
        self,
        anomalies: pd.DataFrame,
        figsize: Optional[Tuple[int, int]] = None
    ) -> Tuple[Figure, Axes]:
        """
        Plot timing anomalies.
        
        Args:
            anomalies: DataFrame with anomalous timing records
            figsize: Custom figure size
            
        Returns:
            Tuple of (figure, axes) objects
        """
        if figsize is None:
            figsize = (12, 6)
        
        if len(anomalies) == 0:
            fig, ax = plt.subplots(figsize=figsize)
            ax.set_title("No Timing Anomalies Found")
            return fig, ax
        
        fig, ax = plt.subplots(figsize=figsize)
        
        # Plot all intervals with anomalies highlighted
        timestamps = anomalies['timestamp']
        intervals = anomalies['time_diff']
        z_scores = anomalies['z_score']
        
        # Normal intervals
        normal = anomalies[abs(anomalies['z_score']) <= 2]
        anom = anomalies[abs(anomalies['z_score']) > 2]
        
        ax.plot(
            normal['timestamp'],
            normal['time_diff'],
            'bo',
            markersize=4,
            alpha=0.5,
            label='Normal'
        )
        ax.plot(
            anom['timestamp'],
            anom['time_diff'],
            'ro',
            markersize=8,
            alpha=0.8,
            label='Anomalous'
        )
        
        ax.set_xlabel("Timestamp")
        ax.set_ylabel("Interval (s)")
        ax.set_title("Timing Anomalies")
        ax.grid(True, alpha=0.3)
        ax.legend()
        
        return fig, ax
    
    # ========================================================================
    # CONFIGURATION ANALYSIS VISUALIZATION
    # ========================================================================
    
    def plot_configuration_comparison(
        self,
        comparison_data: Dict,
        figsize: Optional[Tuple[int, int]] = None
    ) -> Tuple[Figure, List[Axes]]:
        """
        Plot comparison of different Kalman configurations.
        
        Args:
            comparison_data: Dictionary with configuration comparison data
            figsize: Custom figure size
            
        Returns:
            Tuple of (figure, list of axes) objects
        """
        if figsize is None:
            figsize = (12, 8)
        
        if not comparison_data or 'configurations' not in comparison_data:
            fig, ax = plt.subplots(figsize=figsize)
            ax.set_title("No Configuration Data Available")
            return fig, [ax]
        
        configs = comparison_data['configurations']
        
        fig, axes = plt.subplots(2, 2, figsize=figsize)
        axes = [ax for row in axes for ax in row]
        
        # Extract data
        noise_values = [c['position_process_noise'] for c in configs]
        session_counts = [c['session_count'] for c in configs]
        labels = [
            f"PN={c['position_process_noise']}, "
            f"VN={c['velocity_process_noise']}, "
            f"MN={c['position_measurement_noise']}"
            for c in configs
        ]
        
        # Plot session counts
        axes[0].bar(range(len(configs)), session_counts, alpha=0.7)
        axes[0].set_xticks(range(len(configs)))
        axes[0].set_xticklabels(labels, rotation=45, ha='right', fontsize=10)
        axes[0].set_ylabel("Session Count")
        axes[0].set_title("Sessions per Configuration")
        axes[0].grid(True, alpha=0.3)
        
        # Hide unused subplots
        for i in range(1, len(axes)):
            axes[i].axis('off')
        
        fig.suptitle("Configuration Comparison")
        plt.tight_layout()
        
        return fig, axes
    
    def plot_parameter_impact(
        self,
        parameter_data: Dict,
        parameter_name: str,
        figsize: Optional[Tuple[int, int]] = None
    ) -> Tuple[Figure, Axes]:
        """
        Plot impact of a specific parameter on performance.
        
        Args:
            parameter_data: Dictionary with parameter impact data
            parameter_name: Name of the parameter (for title)
            figsize: Custom figure size
            
        Returns:
            Tuple of (figure, axes) objects
        """
        if figsize is None:
            figsize = (12, 6)
        
        if not parameter_data or 'metrics' not in parameter_data:
            fig, ax = plt.subplots(figsize=figsize)
            ax.set_title(f"No Data for {parameter_name} Impact")
            return fig, ax
        
        fig, ax = plt.subplots(figsize=figsize)
        
        metrics = parameter_data['metrics']
        levels = parameter_data.get('noise_levels', parameter_data.get('measurement_noise_levels', []))
        
        if not levels:
            ax.set_title(f"No Levels for {parameter_name}")
            return fig, ax
        
        # Extract a metric to plot (e.g., average covariance)
        metric_name = 'avg_covariance_lat'  # Default
        values = []
        
        for level in levels:
            if level in metrics and metric_name in metrics[level]:
                values.append(metrics[level][metric_name])
            else:
                values.append(0)
        
        ax.plot(levels, values, 'bo-', linewidth=2, markersize=8)
        ax.set_xlabel(parameter_name)
        ax.set_ylabel(metric_name.replace('_', ' ').title())
        ax.set_title(f"Impact of {parameter_name} on {metric_name}")
        ax.grid(True, alpha=0.3)
        
        return fig, ax
    
    # ========================================================================
    # LOOP TIMING VISUALIZATION
    # ========================================================================
    
    def plot_loop_timing(
        self,
        data_update_times: List[float],
        prediction_times: List[float],
        data_update_interval: float = 30.0,
        prediction_interval: float = 2.0,
        figsize: Optional[Tuple[int, int]] = None
    ) -> Tuple[Figure, Axes]:
        """
        Plot loop timing distribution and history.
        
        Args:
            data_update_times: List of execution times for data update loop
            prediction_times: List of execution times for prediction loop
            data_update_interval: Expected interval for data updates
            prediction_interval: Expected interval for predictions
            figsize: Figure size
            
        Returns:
            Tuple of (figure, axes)
        """
        if figsize is None:
            figsize = (14, 10)
        
        fig, axes = plt.subplots(2, 2, figsize=figsize)
        
        # Plot 1: Data update loop timing histogram
        ax1 = axes[0, 0]
        if data_update_times:
            ax1.hist(data_update_times, bins=20, alpha=0.7, color='steelblue', edgecolor='black')
            ax1.axvline(data_update_interval, color='red', linestyle='--', label=f'Target ({data_update_interval}s)')
            ax1.set_xlabel('Execution Time (s)')
            ax1.set_ylabel('Frequency')
            ax1.set_title('Data Update Loop Execution Time Distribution')
            ax1.grid(True, alpha=0.3)
            ax1.legend()
        
        # Plot 2: Prediction loop timing histogram
        ax2 = axes[0, 1]
        if prediction_times:
            ax2.hist(prediction_times, bins=20, alpha=0.7, color='coral', edgecolor='black')
            ax2.axvline(prediction_interval, color='red', linestyle='--', label=f'Target ({prediction_interval}s)')
            ax2.set_xlabel('Execution Time (s)')
            ax2.set_ylabel('Frequency')
            ax2.set_title('Prediction Loop Execution Time Distribution')
            ax2.grid(True, alpha=0.3)
            ax2.legend()
        
        # Plot 3: Data update loop timing over time
        ax3 = axes[1, 0]
        if data_update_times:
            ax3.plot(data_update_times, marker='o', markersize=2, alpha=0.6, color='steelblue')
            ax3.axhline(data_update_interval, color='red', linestyle='--', label=f'Target ({data_update_interval}s)')
            ax3.set_xlabel('Iteration')
            ax3.set_ylabel('Execution Time (s)')
            ax3.set_title('Data Update Loop Execution Time Over Time')
            ax3.grid(True, alpha=0.3)
            ax3.legend()
        
        # Plot 4: Prediction loop timing over time
        ax4 = axes[1, 1]
        if prediction_times:
            ax4.plot(prediction_times, marker='o', markersize=2, alpha=0.6, color='coral')
            ax4.axhline(prediction_interval, color='red', linestyle='--', label=f'Target ({prediction_interval}s)')
            ax4.set_xlabel('Iteration')
            ax4.set_ylabel('Execution Time (s)')
            ax4.set_title('Prediction Loop Execution Time Over Time')
            ax4.grid(True, alpha=0.3)
            ax4.legend()
        
        plt.tight_layout()
        return fig, axes
    
    def plot_loop_timing_box(
        self,
        data_update_times: List[float],
        prediction_times: List[float],
        figsize: Optional[Tuple[int, int]] = None
    ) -> Tuple[Figure, Axes]:
        """
        Plot box plots for loop timing comparison.
        
        Args:
            data_update_times: List of execution times for data update loop
            prediction_times: List of execution times for prediction loop
            figsize: Figure size
            
        Returns:
            Tuple of (figure, axes)
        """
        if figsize is None:
            figsize = (10, 6)
        
        fig, ax = plt.subplots(figsize=figsize)
        
        data = []
        labels = []
        colors = []
        
        if data_update_times:
            data.append(data_update_times)
            labels.append('Data Update Loop')
            colors.append('steelblue')
        
        if prediction_times:
            data.append(prediction_times)
            labels.append('Prediction Loop')
            colors.append('coral')
        
        if data:
            bp = ax.boxplot(data, labels=labels, patch_artist=True)
            for patch, color in zip(bp['boxes'], colors):
                patch.set_facecolor(color)
                patch.set_alpha(0.6)
            ax.set_ylabel('Execution Time (s)')
            ax.set_title('Loop Execution Time Comparison')
            ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        return fig, ax


# Create a global instance for convenience
kalman_visualizer = KalmanVisualizer()


# Convenience functions for direct use in notebooks
def plot_trajectories(predictions: pd.DataFrame, **kwargs) -> Tuple[Figure, Axes]:
    """Convenience function to plot aircraft trajectories."""
    return kalman_visualizer.plot_aircraft_trajectories(predictions, **kwargs)


def plot_covariance(trajectory: pd.DataFrame, **kwargs) -> Tuple[Figure, Axes]:
    """Convenience function to plot covariance over time."""
    return kalman_visualizer.plot_covariance_over_time(trajectory, **kwargs)


def plot_histograms(data: pd.DataFrame, columns: List[str], **kwargs) -> Tuple[Figure, List[Axes]]:
    """Convenience function to plot distribution histograms."""
    return kalman_visualizer.plot_distribution_histograms(data, columns, **kwargs)


def plot_scatter(data: pd.DataFrame, x_col: str, y_col: str, **kwargs) -> Tuple[Figure, Axes]:
    """Convenience function to create scatter plot."""
    return kalman_visualizer.plot_scatter_correlation(data, x_col, y_col, **kwargs)


def plot_3d_trajectory_interactive(predictions: pd.DataFrame,
        measurements: pd.DataFrame, **kwargs) -> Any:
    """Convenience function to create interactive 3D trajectory plot."""
    return kalman_visualizer.plot_3d_trajectory_interactive(predictions, measurements, **kwargs)


def plot_loop_timing(
    data_update_times: List[float],
    prediction_times: List[float],
    **kwargs
) -> Tuple[Figure, Any]:
    """Convenience function to plot loop timing analysis."""
    return kalman_visualizer.plot_loop_timing(
        data_update_times, prediction_times, **kwargs
    )
