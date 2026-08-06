import serial
import serial.tools.list_ports
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import os
import threading
import time
import signal
import sys
from services.aircraft_service import aircraft_service
from services.kalman_filter_service import kalman_filter_service

app = Flask(__name__, static_folder='static')
CORS(app)

# Global serial connection
serial_connection = None
reader_thread = None
shutdown_flag = threading.Event()

def list_serial_ports():
    """Return a list of available serial ports."""
    try:
        ports = serial.tools.list_ports.comports()
        return [port.device for port in ports]
    except Exception as e:
        print(f"Error listing serial ports: {e}")
        return []

def init_serial():
    """Initialize serial connection to /dev/ttyUSB0."""
    global serial_connection, reader_thread
    
    # Clean up any existing connection first
    cleanup_serial()
    
    serial_port = os.environ.get('SERIAL_PORT', '/dev/ttyUSB0')
    serial_rate = os.environ.get('SERIAL_RATE', '9600')
    
    try:
        serial_connection = serial.Serial(
            port=serial_port,
            baudrate=serial_rate,
            timeout=1
        )
        print(f"[SERIAL] Connected to {serial_port} at {serial_rate} baud")
        
        shutdown_flag.clear()
        reader_thread = threading.Thread(target=read_serial, daemon=True)  # Make daemon
        reader_thread.start()
        return True
    except Exception as e:
        print(f"[SERIAL] Error connecting to {serial_port}: {e}")
        serial_connection = None
        return False

def read_serial():
    """Background thread to read from serial port and log messages."""
    global serial_connection
    
    if serial_connection is None:
        return
    
    print("[SERIAL] Starting serial reader thread...")
    
    while serial_connection and serial_connection.is_open and not shutdown_flag.is_set():
        try:
            if serial_connection.in_waiting > 0:
                line = serial_connection.readline().decode('utf-8', errors='ignore').strip()
                if line:
                    print(f"[SERIAL] {line}")
            time.sleep(0.01)  # Small delay to prevent CPU overload
        except serial.SerialException as e:
            print(f"[SERIAL] Connection error: {e}")
            try:
                serial_connection.close()
            except:
                pass
            serial_connection = None
            # Try to reconnect only if not shutting down
            if not shutdown_flag.is_set():
                time.sleep(5)
                init_serial()
            break
        except Exception as e:
            print(f"[SERIAL] Unexpected error: {e}")
            break


def send_serial_command(command_str):
    """Send a command string to the serial port."""
    global serial_connection
    print("serial_connection", serial_connection)
    if serial_connection and serial_connection.is_open:
        try:
            print("command_str", command_str)
            serial_connection.write(command_str.encode('utf-8') + b'\n')
            print(f"[SERIAL] Sent: {command_str}")
            return True
        except Exception as e:
            print(f"[SERIAL] Error sending command: {e}")
            return False
    else:
        print("[SERIAL] Error: Serial port not connected")
        return False


def cleanup_serial():
    """Cleanup serial connection and reader thread on shutdown."""
    global serial_connection, reader_thread
    print("[SERIAL] Cleaning up serial connection...")
    
    # Signal the reader thread to stop
    shutdown_flag.set()
    
    # Close the serial connection first
    if serial_connection and serial_connection.is_open:
        try:
            serial_connection.close()
            print("[SERIAL] Serial port closed")
        except Exception as e:
            print(f"[SERIAL] Error closing serial port: {e}")
        finally:
            serial_connection = None
    
    # Wait for the reader thread to finish (with timeout)
    if reader_thread and reader_thread.is_alive():
        reader_thread.join(timeout=2.0)
        if reader_thread.is_alive():
            print("[SERIAL] Warning: Reader thread did not stop gracefully")
        else:
            print("[SERIAL] Reader thread stopped")


def signal_handler(sig, frame):
    """Handle shutdown signals gracefully."""
    print(f"\n[SERIAL] Received signal {sig}, shutting down...")
    cleanup_serial()
    sys.exit(0)

# Basic health check endpoint
@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({"status": "ok", "message": "Turret server is running"}), 200


# Endpoint to get turret status
@app.route('/api/turret/status', methods=['GET'])
def get_status():
    # TODO: Implement actual turret status retrieval
    return jsonify({
        "azimuth": 0,
        "elevation": 0,
        "is_armed": False,
        "battery_level": 100
    }), 200


# Endpoint to send turret commands
@app.route('/api/turret/command', methods=['POST'])
def send_command():
    data = request.get_json()
    print("hit")
    
    if data is None:
        return jsonify({"status": "error", "error": "No JSON data provided"}), 400
    
    # Check for azimuth and elevation
    if 'azimuth' not in data or 'elevation' not in data:
        return jsonify({
            "status": "error", 
            "error": "Both 'azimuth' and 'elevation' are required"
        }), 400
    
    try:
        azimuth = float(data['azimuth'])
        elevation = float(data['elevation'])
    except (ValueError, TypeError) as e:
        return jsonify({
            "status": "error",
            "error": f"azimuth and elevation must be valid numbers: {e}"
        }), 400
    
    # Format the command string
    command_str = "moveto 60.0 50.0"
    
    # Send via serial
    success = send_serial_command(command_str)
    
    if success:
        return jsonify({
            "status": "success",
            "command": command_str,
            "azimuth": azimuth,
            "elevation": elevation
        }), 200
    else:
        return jsonify({
            "status": "error",
            "error": "Failed to send command to serial port"
        }), 500

# Endpoint to list available serial ports
@app.route('/api/serial/ports', methods=['GET'])
def get_serial_ports():
    ports = list_serial_ports()
    return jsonify({
        "ports": ports,
        "count": len(ports),
        "default": os.environ.get('SERIAL_PORT', '/dev/ttyUSB0'),
        "connected": serial_connection is not None and serial_connection.is_open
    }), 200

@app.route('/api/serial/connect', methods=['GET'])
def connect_serial():
    ports = list_serial_ports()
    print("ports", ports)

    return jsonify({
        "ports": ports,
        "count": len(ports),
        "default": os.environ.get('SERIAL_PORT', '/dev/ttyUSB0'),
        "connected": serial_connection is not None and serial_connection.is_open
    }), 200

# Endpoint for serial communication with firmware
@app.route('/api/serial/moveto', methods=['GET', 'POST'])
def send_serial():
    if request.method == 'POST':
        data = request.get_json()
        message = data.get('message', {}) if data else {}
        
        if message and 'azimuth' in message and 'elevation' in message:
            moveto_cmd = f"moveto {message['azimuth']} {message['elevation']}"
            print("moveto_cmd", moveto_cmd)
            success = send_serial_command(moveto_cmd)
            if success:
                return jsonify({"status": "sent to serial", "message": message}), 200
            else:
                return jsonify({"status": "error", "error": "Serial port not connected"}), 500
        else:
            return jsonify({"status": "error", "error": "No message provided"}), 400
    else:
        return jsonify({"status": "ready", "message": "POST to this endpoint to send serial data"}), 200


# Aircraft Data API Endpoints
@app.route('/api/aircraft', methods=['GET'])
def get_aircraft():
    """
    Get aircraft data for the default Toulouse area or a custom bounding box.
    
    Query parameters:
    - lat_min: Minimum latitude (default: 42.8448)
    - lat_max: Maximum latitude (default: 44.1972)
    - lon_min: Minimum longitude (default: 0.6213)
    - lon_max: Maximum longitude (default: 2.2152)
    """
    try:
        lat_min = request.args.get('lat_min', type=float)
        lat_max = request.args.get('lat_max', type=float)
        lon_min = request.args.get('lon_min', type=float)
        lon_max = request.args.get('lon_max', type=float)
        
        data = aircraft_service.get_aircraft_in_area(
            lat_min=lat_min,
            lat_max=lat_max,
            lon_min=lon_min,
            lon_max=lon_max,
        )
        
        return jsonify(data), 200
        
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500


@app.route('/api/aircraft/position', methods=['GET'])
def get_aircraft_by_position():
    """
    Get aircraft data around a specific GPS position.
    
    Query parameters:
    - lat: Latitude of center point (required)
    - lon: Longitude of center point (required)
    - radius_km: Search radius in kilometers (default: 100)
    """
    try:
        latitude = request.args.get('lat', type=float)
        longitude = request.args.get('lon', type=float)
        radius_km = request.args.get('radius_km', default=100.0, type=float)
        
        if latitude is None or longitude is None:
            return jsonify({
                "status": "error",
                "error": "lat and lon query parameters are required"
            }), 400
        
        data = aircraft_service.get_aircraft_at_position(
            latitude=latitude,
            longitude=longitude,
            radius_km=radius_km,
        )
        
        return jsonify(data), 200
        
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500


# Kalman Filter API Endpoints
@app.route('/api/kalman/predictions', methods=['GET'])
def get_kalman_predictions():
    """
    Get the latest position predictions for all tracked flights.
    
    Returns:
        Dictionary of callsign -> prediction data
    """
    try:
        predictions = kalman_filter_service.get_latest_predictions()
        return jsonify({
            "predictions": predictions,
            "count": len(predictions),
            "timestamp": time.time()
        }), 200
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500


@app.route('/api/kalman/prediction/<callsign>', methods=['GET'])
def get_kalman_prediction(callsign):
    """
    Get the latest position prediction for a specific flight.
    
    Args:
        callsign: The flight callsign (URL parameter)
    """
    try:
        prediction = kalman_filter_service.get_prediction_for_flight(callsign)
        
        if prediction is None:
            return jsonify({
                "status": "not_found",
                "error": f"No prediction available for callsign: {callsign}"
            }), 404
        
        return jsonify({
            "callsign": callsign,
            "prediction": prediction
        }), 200
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500


@app.route('/api/kalman/stats', methods=['GET'])
def get_kalman_stats():
    """
    Get statistics and status of the Kalman filter service.
    
    Returns:
        Service statistics including track count, prediction count, etc.
    """
    try:
        stats = kalman_filter_service.get_statistics()
        return jsonify(stats), 200
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500


@app.route('/api/kalman/start', methods=['POST'])
def start_kalman_service():
    """
    Start the Kalman filter service (background threads).
    """
    try:
        kalman_filter_service.start()
        return jsonify({
            "status": "started",
            "message": "Kalman filter service started"
        }), 200
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500


@app.route('/api/kalman/stop', methods=['POST'])
def stop_kalman_service():
    """
    Stop the Kalman filter service (background threads).
    """
    try:
        kalman_filter_service.stop()
        return jsonify({
            "status": "stopped",
            "message": "Kalman filter service stopped"
        }), 200
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500


# Serve React App - Static files
# This catch-all must come AFTER all API routes
# In development, the frontend is served from Vite on port 5173
# This is only for production when static files are in the server
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    # Skip if this is an API request
    if path and path.startswith('api/'):
        return jsonify({"error": "API endpoint not found. Use POST for commands."}), 404
    # Serve static files if they exist
    if path != "" and os.path.exists("static/" + path):
        return send_from_directory('static', path)
    # Fallback to index.html for SPA routing
    return send_from_directory('static', 'index.html')


if __name__ == '__main__':
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    print("SERVER STARTING AAAAAAAAAAAAAAAAAAAAAAAAAAHHHHHHHHHh")
    
    # Initialize serial connection
    
    ports = list_serial_ports()
    print(f"Available serial ports: {ports}")
    init_serial()
    if not ports:
        print("[SERIAL] Warning: No serial ports found!")
    
    try:
        # Start Kalman filter service
        print("[KALMAN] Starting Kalman filter service on server startup...")
        kalman_filter_service.start()
        
        app.run(host='0.0.0.0', port=5000, debug=True)
    finally:
        # Ensure cleanup on any exit
        cleanup_serial()
        kalman_filter_service.stop()
