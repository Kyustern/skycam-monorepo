# Jupyter Notebook Requirements: Captured Data Analysis

## Overview

This document outlines the requirements for a Jupyter notebook that analyzes captured aircraft tracking and Kalman filter prediction data from the TURRET system's storage backend.

## Data Sources

The notebook will analyze data stored by `CSVStorageBackend` in the following structure:

```
captures/
└── YYYY-MM-DD/
    └── HH-MM-SS_session_XXXX/
        ├── metadata.json          # Session metadata & Kalman config
        ├── predictions.csv        # Kalman filter predictions (flattened)
        ├── opensky_data.csv       # OpenSky aircraft data (flattened)
        └── statistics.csv         # Time-series statistics
```

## Input Data Schema

### predictions.csv
| Column | Type | Description |
|--------|------|-------------|
| timestamp | float | Unix timestamp of capture |
| frame_index | int | Sequential frame counter |
| session_id | str | Unique session identifier |
| callsign | str | Aircraft callsign |
| latitude | float | Latitude in decimal degrees |
| longitude | float | Longitude in decimal degrees |
| baro_altitude | float | Barometric altitude in meters |
| velocity | float | Velocity in knots |
| true_track | float | True track angle in degrees |
| vertical_rate | float | Vertical rate in m/s |
| covariance_lat | float | Latitude covariance from Kalman filter |
| covariance_lon | float | Longitude covariance from Kalman filter |
| covariance_alt | float | Altitude covariance from Kalman filter |
| state | str | Kalman filter state (tracking, coasting, etc.) |
| v_north | float | North component of velocity (m/s) |
| v_east | float | East component of velocity (m/s) |

### opensky_data.csv
| Column | Type | Description |
|--------|------|-------------|
| timestamp | float | Unix timestamp of capture |
| frame_index | int | Sequential frame counter |
| session_id | str | Unique session identifier |
| callsign | str | Aircraft callsign |
| latitude | float | Latitude in decimal degrees |
| longitude | float | Longitude in decimal degrees |
| baro_altitude | float | Barometric altitude in meters |
| velocity | float | Velocity in knots |
| true_track | float | True track angle in degrees |
| vertical_rate | float | Vertical rate in m/s |
| on_ground | bool | Whether aircraft is on ground |
| v_north | float | North component of velocity (m/s) |
| v_east | float | East component of velocity (m/s) |

### statistics.csv
| Column | Type | Description |
|--------|------|-------------|
| timestamp | float | Unix timestamp of capture |
| frame_index | int | Sequential frame counter |
| session_id | str | Unique session identifier |
| track_count | int | Number of tracked aircraft |
| prediction_count | int | Number of predictions generated |
| total_predictions | int | Cumulative predictions count |
| total_measurements | int | Cumulative measurements count |

### metadata.json
Contains session configuration including:
- Kalman filter parameters (process noise, measurement noise, intervals)
- Capture location (latitude, longitude, radius_km)
- Session start/end times
- TURRET version and file format version

## Notebook Requirements

### Functional Requirements

#### 1. Data Loading
- [ ] Load data from CSV files (predictions, opensky_data, statistics)
- [ ] Parse metadata.json for session configuration
- [ ] Handle multiple session directories
- [ ] Support loading data from a specific date or date range
- [ ] Provide summary statistics of loaded data

#### 2. Data Exploration
- [ ] Display basic statistics (counts, means, std dev) for all numeric columns
- [ ] Show unique values for categorical columns (callsign, state)
- [ ] Plot data availability over time
- [ ] Identify data gaps or missing values
- [ ] Display Kalman filter configuration from metadata

#### 3. Aircraft Tracking Analysis
- [ ] Track individual aircraft across frames
- [ ] Plot aircraft trajectories on a map (latitude vs longitude)
- [ ] Calculate and display track continuity metrics
- [ ] Identify track gaps and handoffs between predictions
- [ ] Analyze track accuracy by comparing predictions vs OpenSky data

#### 4. Kalman Filter Performance
- [ ] Plot covariance values over time for each dimension (lat, lon, alt)
- [ ] Analyze covariance convergence for tracked aircraft
- [ ] Calculate prediction error statistics (RMSE, MAE)
- [ ] Compare predicted vs actual positions
- [ ] Analyze state transitions (tracking -> coasting -> lost)
- [ ] Plot velocity vector accuracy (v_north, v_east)

#### 5. Statistical Analysis
- [ ] Plot aircraft count over time
- [ ] Analyze prediction/measurement rates
- [ ] Calculate track stability metrics
- [ ] Identify anomalous tracks or predictions
- [ ] Analyze altitude distribution and changes

#### 6. Temporal Analysis
- [ ] Plot data update intervals
- [ ] Analyze frame timing consistency
- [ ] Identify timing anomalies or delays
- [ ] Correlate timing with prediction quality

#### 7. Configuration Analysis
- [ ] Compare performance across different Kalman configurations
- [ ] Analyze impact of process noise parameters
- [ ] Analyze impact of measurement noise parameters
- [ ] Evaluate update interval effects
- [ ] Generate configuration recommendations

#### 8. Visualization
- [ ] Interactive aircraft trajectory plots
- [ ] Time-series plots for key metrics
- [ ] Histograms for distributions
- [ ] Scatter plots for correlations
- [ ] Heatmaps for spatial density
- [ ] 3D plots for altitude analysis

### Non-Functional Requirements

#### Performance
- Efficiently handle datasets with 10,000+ frames
- Load and process data in reasonable time (< 10 seconds for typical sessions)
- Use appropriate data structures (pandas DataFrames, numpy arrays)

#### Usability
- Clear cell documentation and markdown explanations
- Logical flow from data loading to analysis
- Reproducible results with seed values where applicable
- Error handling for missing or malformed data

#### Maintainability
- Modular code organization within notebook
- Reusable utility functions
- Clear variable naming following data domain
- Comments explaining non-obvious logic

### Technical Stack

**Required Python Packages:**
- pandas >= 2.0.0 (data manipulation)
- numpy >= 1.24.0 (numerical operations)
- matplotlib >= 3.7.0 (basic plotting)
- seaborn >= 0.12.0 (statistical visualization)
- scipy >= 1.10.0 (statistical functions)
- jupyter >= 1.0.0 (notebook environment)
- ipython >= 8.0.0 (interactive Python)

**Optional Packages:**
- plotly >= 5.0.0 (interactive visualizations)
- folium >= 0.14.0 (interactive maps)
- cartopy >= 0.21.0 (geospatial projections)
- pyarrow >= 1.0.0 (efficient CSV/parquet I/O)
- h5py >= 3.8.0 (HDF5 file support)
- tqdm >= 4.64.0 (progress bars)

**Development Tools:**
- pytest (for testing utility functions)
- black (code formatting)
- mypy (type checking)

## Deliverables

1. **Data Loading Module**: Functions to load and parse capture data
2. **Analysis Module**: Functions for each analysis category
3. **Visualization Module**: Reusable plotting functions
4. **Main Notebook**: kalman-tuning.ipynb with comprehensive analysis
5. **Configuration**: requirements.txt with all dependencies

## Data Quality Assumptions

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
