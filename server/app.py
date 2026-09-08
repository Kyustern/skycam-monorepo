import serial
import serial.tools.list_ports
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from flask_socketio import emit
from socketio_instance import init_socketio, get_socketio
import os
import threading
import time
import signal
import sys
from services.aircraft_service import aircraft_service
from services.kalman_filter_service import kalman_filter_service
from services.data_capture_service import data_capture_service
from utils.logger import serial_logger, websocket_logger, server_logger

app = Flask(__name__, static_folder='static')
CORS(app)

# Initialize SocketIO
init_socketio(app, cors_allowed_origins="*", async_mode='threading', path="/api/ws")
socketio = get_socketio()

# Global serial connection
serial_connection = None
reader_thread = None
shutdown_flag = threading.Event()

# WebSocket heartbeat
heartbeat_thread = None
heartbeat_active = False
connected_clients = set()
heartbeat_lock = threading.Lock()

# Heartbeat interval (500ms)
HEARTBEAT_INTERVAL = 5.0
def list_serial_ports():
    """Return a list of available serial ports."""
    try:
        ports = serial.tools.list_ports.comports()
        return [port.device for port in ports]
    except Exception as e:
        serial_logger.error(f"Error listing serial ports: {e}")
        return []

def init_serial():
    """Initialize serial connection to /dev/ttyUSB0."""
    global serial_connection, reader_thread
    
    # Clean up any existing connection first
    cleanup_serial()
    
    serial_port = os.environ.get('SERIAL_PORT', '/dev/ttyUSB1')
    serial_rate = os.environ.get('SERIAL_RATE', '9600')
    
    try:
        serial_connection = serial.Serial(
            port=serial_port,
            baudrate=serial_rate,
            timeout=1
        )
        serial_logger.info(f"Connected to {serial_port} at {serial_rate} baud")
        
        shutdown_flag.clear()
        reader_thread = threading.Thread(target=read_serial, daemon=True)  # Make daemon
        reader_thread.start()
        return True
    except Exception as e:
        serial_logger.error(f"Error connecting to {serial_port}: {e}")
        serial_connection = None
        return False

def read_serial():
    """Background thread to read from serial port and log messages."""
    global serial_connection
    
    if serial_connection is None:
        return
    
    serial_logger.info("Starting serial reader thread...")
    
    while serial_connection and serial_connection.is_open and not shutdown_flag.is_set():
        try:
            if serial_connection.in_waiting > 0:
                line = serial_connection.readline().decode('utf-8', errors='ignore').strip()
                if line:
                    serial_logger.info(line)
            time.sleep(0.01)  # Small delay to prevent CPU overload
        except serial.SerialException as e:
            serial_logger.error(f"Connection error: {e}")
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
            serial_logger.error(f"Unexpected error: {e}")
            break


def send_serial_command(command_str):
    """Send a command string to the serial port."""
    global serial_connection
    serial_logger.debug(f"Sending command, connection: {serial_connection}")
    if serial_connection and serial_connection.is_open:
        try:
            serial_logger.debug(f"Command to send: {command_str}")
            serial_connection.write(command_str.encode('utf-8') + b'\n')
            serial_logger.info(f"Sent: {command_str}")
            return True
        except Exception as e:
            serial_logger.error(f"Error sending command: {e}")
            return False
    else:
        serial_logger.error("Serial port not connected")
        return False


def cleanup_serial():
    """Cleanup serial connection and reader thread on shutdown."""
    global serial_connection, reader_thread
    serial_logger.info("Cleaning up serial connection...")
    
    # Signal the reader thread to stop
    shutdown_flag.set()
    
    # Close the serial connection first
    if serial_connection and serial_connection.is_open:
        try:
            serial_connection.close()
            serial_logger.info("Serial port closed")
        except Exception as e:
            serial_logger.error(f"Error closing serial port: {e}")
        finally:
            serial_connection = None
    
    # Wait for the reader thread to finish (with timeout)
    if reader_thread and reader_thread.is_alive():
        reader_thread.join(timeout=2.0)
        if reader_thread.is_alive():
            serial_logger.warning("Reader thread did not stop gracefully")
        else:
            serial_logger.info("Reader thread stopped")


def signal_handler(sig, frame):
    """Handle shutdown signals gracefully."""
    server_logger.info(f"Received signal {sig}, shutting down...")
    cleanup_serial()
    kalman_filter_service.stop()
    stop_heartbeat()
    sys.exit(0)


def heartbeat_loop():
    """Background thread that sends heartbeat to all connected WebSocket clients every 500ms."""
    global heartbeat_active
    websocket_logger.info("Starting heartbeat loop...")
    
    while heartbeat_active:
        with heartbeat_lock:
            # Getting the freshest prediction data
            predictions = kalman_filter_service.get_latest_predictions()

            # Send heartbeat to all connected clients
            for sid in list(connected_clients):
                socketio.emit('heartbeat', time.time(), room=sid)
        
        # Sleep for the heartbeat interval
        time.sleep(HEARTBEAT_INTERVAL)
    
    websocket_logger.info("Heartbeat loop stopped")


def start_heartbeat():
    """Start the heartbeat thread."""
    global heartbeat_active, heartbeat_thread
    
    try:
        if heartbeat_active:
            return
        
        heartbeat_active = True
        heartbeat_thread = threading.Thread(
            target=heartbeat_loop,
            daemon=True,
            name="websocket-heartbeat"
        )
        heartbeat_thread.start()
        websocket_logger.info("Heartbeat started")
    except Exception as e:
        print("e", e)


def stop_heartbeat():
    """Stop the heartbeat thread."""
    global heartbeat_active, heartbeat_thread
    
    heartbeat_active = False
    if heartbeat_thread and heartbeat_thread.is_alive():
        heartbeat_thread.join(timeout=1.0)
    websocket_logger.info("Heartbeat stopped")


# WebSocket event handlers
@socketio.on('connect')
def handle_connect():
    with heartbeat_lock:
        connected_clients.add(request.sid)
    websocket_logger.info(f"Client connected: {request.sid} (Total: {len(connected_clients)})")
    socketio.emit('connected', f"one guy succesfully connected on the server ! sid : {request.sid}")


@socketio.on('disconnect')
def handle_disconnect():
    with heartbeat_lock:
        connected_clients.discard(request.sid)
    websocket_logger.info(f"Client disconnected: {request.sid} (Total: {len(connected_clients)})")


@socketio.on('moveto')
def handle_moveto(data):
    global server_start
    server_logger.debug(f"Received a moveto command at {time.time() - server_start}")
    moveto_cmd = f"moveto {data['azimuth']} {data['elevation']}"
    success = send_serial_command(moveto_cmd)
    if success:
        server_logger.debug(f"Sending moveto command: {moveto_cmd}")


# Basic health check endpoint
@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({"status": "ok", "message": "Turret server is running"}), 200

# Endpoint to send turret commands
@app.route('/api/turret/command', methods=['POST'])
def send_command():
    data = request.get_json()
    server_logger.debug("Command endpoint hit")
    
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
    server_logger.debug(f"Available ports: {ports}")

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
            server_logger.debug(f"Sending moveto command: {moveto_cmd}")
            success = send_serial_command(moveto_cmd)
            if success:
                return jsonify({"status": "sent to serial", "message": message}), 200
            else:
                return jsonify({"status": "error", "error": "Serial port not connected"}), 500
        else:
            return jsonify({"status": "error", "error": "No message provided"}), 400
    else:
        return jsonify({"status": "ready", "message": "POST to this endpoint to send serial data"}), 200


@app.route('/api/aircraft/position', methods=['POST'])
def get_aircraft_by_position():
    """
    Get aircraft data around a specific GPS position.
    
    JSON body parameters:
    - lat: Latitude of center point (required)
    - lon: Longitude of center point (required)
    - radius_km: Search radius in kilometers (default: 100)
    """
    try:
        body = request.get_json()
        print("body", body)
        if not body:
            return jsonify({
                "status": "error",
                "error": "Request body must be JSON"
            }), 400
        
        latitude = body.get('lat')
        longitude = body.get('lon')
        radius_km = body.get('radius_km', 100.0)
        
        if latitude is None or longitude is None:
            return jsonify({
                "status": "error",
                "error": "lat and lon are required in request body"
            }), 400
        
        # Convert to float
        latitude = float(latitude)
        longitude = float(longitude)
        radius_km = float(radius_km)
        
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


# Data Capture Service Endpoints

@app.route('/api/capture/status', methods=['GET'])
def get_capture_status():
    """
    Get the current status of the data capture service.
    
    Returns:
        Dictionary with service status information
    """
    try:
        status = data_capture_service.get_status()
        return jsonify(status), 200
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500


@app.route('/api/capture/files', methods=['GET'])
def get_capture_files():
    """
    Get a list of all capture files.
    
    Returns:
        Dictionary with list of files and count
    """
    try:
        files = data_capture_service.get_capture_files()
        return jsonify({"files": files, "count": len(files)}), 200
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500


@app.route('/api/capture/start', methods=['POST'])
def start_capture():
    """
    Start the data capture service.
    """
    try:
        data_capture_service.start()
        return jsonify({
            "status": "started",
            "message": "Data capture service started"
        }), 200
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500


@app.route('/api/capture/stop', methods=['POST'])
def stop_capture():
    """
    Stop the data capture service.
    """
    try:
        data_capture_service.stop()
        status = data_capture_service.get_status()
        return jsonify({
            "status": "stopped",
            "message": "Data capture service stopped",
            "frames_captured": status["frames_captured"],
            "file": status["current_file"]
        }), 200
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500


@app.route('/api/capture/config', methods=['GET'])
def get_capture_config():
    """
    Get the current configuration of the capture service.
    
    Returns:
        Dictionary with configuration and Kalman filter settings
    """
    try:
        config = {
            "capture_dir": data_capture_service.CAPTURE_DIR,
            "session_duration": data_capture_service.SESSION_DURATION,
            "max_file_size": data_capture_service.MAX_FILE_SIZE,
            "kalman_config": kalman_filter_service.get_statistics()
        }
        return jsonify(config), 200
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

    server_start = time.time()
    
    # Initialize serial connection
    ports = list_serial_ports()
    server_logger.info(f"Available serial ports: {ports}")
    init_serial()
    if not ports:
        serial_logger.warning("No serial ports found!")
    
    try:
        # Start WebSocket heartbeat
        websocket_logger.info("Starting heartbeat service...")
        start_heartbeat()
        
        # Start Kalman filter service (only in main worker process, not reloader)
        # Flask's reloader sets WERKZEUG_RUN_MAIN='true' in the worker process
        is_main_worker = os.environ.get('WERKZEUG_RUN_MAIN') == 'true'
        if is_main_worker:
            server_logger.info("Starting Kalman filter service on server startup...")
            kalman_filter_service.start()
            
            # Start data capture service
            server_logger.info("Starting data capture service on server startup...")
            data_capture_service.start()
        else:
            server_logger.info("Skipping Kalman filter service start (Flask reloader process)")
            server_logger.info("Skipping data capture service start (Flask reloader process)")
        
        socketio.run(app, host='0.0.0.0', port=5000, debug=True)
    finally:
        # Ensure cleanup on any exit
        cleanup_serial()
        kalman_filter_service.stop()
        data_capture_service.stop()
        stop_heartbeat()
