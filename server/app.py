import serial
import serial.tools.list_ports
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import os
import threading
import time
from services.aircraft_service import aircraft_service

app = Flask(__name__, static_folder='static')
CORS(app)

# Global serial connection
serial_connection = None

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
    global serial_connection
    serial_port = os.environ.get('SERIAL_PORT', '/dev/ttyUSB0')
    serial_rate = os.environ.get('SERIAL_RATE', '9600')
    
    try:
        # Close existing connection if any
        if serial_connection and serial_connection.is_open:
            serial_connection.close()
        
        # Open new connection
        serial_connection = serial.Serial(
            port=serial_port,
            baudrate=serial_rate,
            timeout=1
        )
        print(f"[SERIAL] Connected to {serial_port} at {serial_rate} baud")
        
        # Start background reader thread
        reader_thread = threading.Thread(target=read_serial, daemon=True)
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
    
    while serial_connection and serial_connection.is_open:
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
            # Try to reconnect
            time.sleep(5)
            init_serial()
            break
        except Exception as e:
            print(f"[SERIAL] Unexpected error: {e}")
            break


def send_serial_command(command_str):
    """Send a command string to the serial port."""
    global serial_connection
    if serial_connection and serial_connection.is_open:
        try:
            serial_connection.write(command_str.encode('utf-8') + b'\n')
            print(f"[SERIAL] Sent: {command_str}")
            return True
        except Exception as e:
            print(f"[SERIAL] Error sending command: {e}")
            return False
    else:
        print("[SERIAL] Error: Serial port not connected")
        return False


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
    command_str = f"moveto {azimuth} {elevation}"
    
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


# Endpoint for serial communication with firmware
@app.route('/api/serial/send', methods=['GET', 'POST'])
def send_serial():
    if request.method == 'POST':
        data = request.get_json()
        message = data.get('message', '') if data else ''
        
        if message:
            success = send_serial_command(message)
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
    # Initialize serial connection
    init_serial()
    
    ports = list_serial_ports()
    print(f"Available serial ports: {ports}")
    if not ports:
        print("[SERIAL] Warning: No serial ports found!")
    
    app.run(host='0.0.0.0', port=5000, debug=True)
