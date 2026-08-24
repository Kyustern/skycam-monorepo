# Kalman Filter Analysis Modules

This directory contains Python modules for analyzing TURRET captured data for Kalman filter tuning and performance analysis.

## Module Structure

```
modules/
├── __init__.py           # Package initialization
├── data_loader.py        # Data loading and parsing functions
├── analysis.py           # Analysis functions for all categories
├── visualization.py     # Visualization and plotting functions
└── README.md            # This file
```

## Modules Overview

### 1. `data_loader.py`

**Purpose**: Load and parse captured aircraft tracking and Kalman filter prediction data from the TURRET system's CSV storage backend.

**Key Classes**:
- `SessionMetadata`: Container for session metadata from metadata.json
- `SessionData`: Container for all data from a single capture session
- `DataLoader`: Main class with methods to load and manage capture data

**Key Functions**:
- `load_session()`: Load all data from a single session directory
- `load_sessions()`: Load data from multiple session directories
- `load_all_data()`: Load and merge data from all matching sessions
- `get_session_summary()`: Generate summary statistics for a session
- `get_combined_summary()`: Generate combined summary for all loaded data
- `find_available_dates()`: Find all available dates with capture data
- `find_sessions_for_date()`: Find all session directories for a specific date

**Convenience Functions**:
- `load_session_data()`: Direct function to load a single session
- `load_all_sessions()`: Direct function to load all sessions
- `get_available_dates()`: Direct function to get available dates

### 2. `analysis.py`

**Purpose**: Comprehensive analysis functions for Kalman filter data, including aircraft tracking, Kalman filter performance, statistical analysis, temporal analysis, and configuration analysis.

**Key Classes**:
- `TrackContinuityMetrics`: Metrics for track continuity analysis
- `PredictionErrorMetrics`: Metrics for prediction error analysis
- `CovarianceAnalysis`: Results of covariance convergence analysis
- `KalmanAnalysis`: Main analysis class with all analysis functions

**Analysis Categories**:

#### Data Exploration
- `get_basic_statistics()`: Basic statistics for all numeric columns
- `get_unique_values()`: Unique values for categorical columns
- `identify_data_gaps()`: Identify data gaps and missing values
- `plot_data_availability()`: Prepare data for plotting availability over time

#### Aircraft Tracking Analysis
- `get_aircraft_trajectories()`: Extract trajectories for individual aircraft
- `calculate_track_continuity()`: Calculate track continuity metrics
- `analyze_track_accuracy()`: Analyze track accuracy by comparing predictions vs OpenSky data

#### Kalman Filter Performance
- `analyze_covariance_convergence()`: Analyze covariance convergence for tracked aircraft
- `analyze_state_transitions()`: Analyze state transitions (tracking -> coasting -> lost)
- `calculate_prediction_error_statistics()`: Calculate overall prediction error statistics (RMSE, MAE)
- `analyze_velocity_vector_accuracy()`: Analyze velocity vector accuracy (v_north, v_east)

#### Statistical Analysis
- `analyze_aircraft_count()`: Analyze aircraft count over time
- `analyze_prediction_measurement_rates()`: Analyze prediction and measurement rates
- `calculate_track_stability_metrics()`: Calculate track stability metrics
- `identify_anomalous_tracks()`: Identify anomalous tracks based on covariance and position jumps
- `analyze_altitude_distribution()`: Analyze altitude distribution and changes

#### Temporal Analysis
- `analyze_update_intervals()`: Analyze data update intervals
- `analyze_frame_timing_consistency()`: Analyze frame timing consistency
- `identify_timing_anomalies()`: Identify timing anomalies or delays
- `correlate_timing_with_prediction_quality()`: Correlate timing with prediction quality

#### Configuration Analysis
- `compare_configurations()`: Compare performance across different Kalman configurations
- `analyze_process_noise_impact()`: Analyze impact of process noise parameters
- `analyze_measurement_noise_impact()`: Analyze impact of measurement noise parameters
- `evaluate_update_interval_effects()`: Evaluate effects of update interval on performance
- `generate_configuration_recommendations()`: Generate Kalman filter configuration recommendations

**Global Instance**:
- `kalman_analysis`: Pre-instantiated `KalmanAnalysis` object for convenience

### 3. `visualization.py`

**Purpose**: Reusable plotting functions for visualizing TURRET captured data and Kalman filter analysis results.

**Key Class**:
- `KalmanVisualizer`: Main visualization class with all plotting functions

**Visualization Categories**:

#### Aircraft Trajectory Visualization
- `plot_aircraft_trajectories()`: Plot aircraft trajectories on a 2D map (latitude vs longitude)
- `plot_interactive_trajectory_map()`: Create an interactive-style trajectory plot with velocity vectors
- `plot_3d_trajectory()`: Create a 3D plot for altitude analysis

#### Kalman Filter Performance Visualization
- `plot_covariance_over_time()`: Plot covariance values over time for each dimension (lat, lon, alt)
- `plot_covariance_comparison()`: Plot covariance comparison for multiple aircraft
- `plot_prediction_errors()`: Plot prediction error statistics
- `plot_state_transition_matrix()`: Plot state transition matrix as a heatmap

#### Statistical Visualization
- `plot_aircraft_count()`: Plot aircraft count over time
- `plot_distribution_histograms()`: Plot histograms for distributions of specified columns
- `plot_scatter_correlation()`: Create scatter plot for correlation analysis
- `plot_spatial_density_heatmap()`: Create heatmap for spatial density of predictions

#### Temporal Analysis Visualization
- `plot_update_intervals()`: Plot data update interval analysis
- `plot_timing_anomalies()`: Plot timing anomalies

#### Configuration Analysis Visualization
- `plot_configuration_comparison()`: Plot comparison of different Kalman configurations
- `plot_parameter_impact()`: Plot impact of a specific parameter on performance

**Global Instance**:
- `kalman_visualizer`: Pre-instantiated `KalmanVisualizer` object for convenience

**Convenience Functions**:
- `plot_trajectories()`: Convenience function to plot aircraft trajectories
- `plot_covariance()`: Convenience function to plot covariance over time
- `plot_histograms()`: Convenience function to plot distribution histograms
- `plot_scatter()`: Convenience function to create scatter plot

## Usage

### Basic Usage in Notebook

```python
# Import modules
from modules.data_loader import create_data_loader
from modules.analysis import kalman_analysis
from modules.visualization import kalman_visualizer

# Create data loader
data_loader = create_data_loader('captures')

# Load data
predictions, opensky, statistics, metadata_list = data_loader.load_all_data()

# Run analysis
error_stats = kalman_analysis.calculate_prediction_error_statistics(predictions, opensky)

# Create visualizations
fig, ax = kalman_visualizer.plot_aircraft_trajectories(predictions)
plt.show()
```

### Running as Standalone Script

```python
import sys
sys.path.insert(0, '/path/to/modules')

from data_loader import create_data_loader
from analysis import kalman_analysis

# Use the modules...
```

## Dependencies

All modules require the following Python packages (specified in `requirements.txt`):

- **pandas** >= 2.0.0 (data manipulation)
- **numpy** >= 1.24.0 (numerical operations)
- **matplotlib** >= 3.7.0 (basic plotting)
- **seaborn** >= 0.12.0 (statistical visualization)
- **scipy** >= 1.10.0 (statistical functions)

## Design Principles

1. **Modularity**: Each module has a clear, focused purpose
2. **Reusability**: Functions are designed to be reused across different analyses
3. **Documentation**: All functions and classes are thoroughly documented
4. **Error Handling**: Graceful handling of missing or malformed data
5. **Performance**: Efficient handling of large datasets (10,000+ frames)

## Data Quality Assumptions

The modules make the following assumptions about input data:

- CSV files are well-formed with headers matching the schema
- Timestamps are monotonically increasing within a session
- metadata.json is valid JSON with expected fields
- Coordinate values are in decimal degrees (WGS84)
- Altitude values are in meters
- Velocity values are in knots
- Angular values are in degrees

## Known Limitations

- HDF5 format (.h5 files) may coexist with CSV files but CSV is primary
- Session rotation may create gaps in continuous analysis
- Multiple simultaneous sessions are not merged automatically
- Location data is relative to the turret's configured location

## Version

**Modules Version**: 1.0.0

**Last Updated**: 2026-08-24

## License

These modules are part of the TURRET project and are licensed under the same terms as the main project.
