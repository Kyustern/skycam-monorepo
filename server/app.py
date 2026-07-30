import serial
import serial.tools.list_ports
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import os
import threading
import time

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
    serial_baud_rate = os.environ.get('SERIAL_BAUDRATE', '9600')
    
    try:
        # Close existing connection if any
        if serial_connection and serial_connection.is_open:
            serial_connection.close()
        
        # Open new connection
        serial_connection = serial.Serial(
            port=serial_port,
            baudrate=serial_baud_rate,
            timeout=1
        )
        print(f"[SERIAL] Connected to {serial_port} at 115200 baud")
        
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
@app.route('/api/turret/command', methods=['GET', 'POST'])
def send_command():
    if request.method == 'POST':
        data = request.get_json()
        # TODO: Implement actual command sending to turret
        # Expected commands: { "action": "move", "azimuth": 45, "elevation": 30 }
        # or { "action": "fire" }
        print(f"[SERIAL] Command received: {data}")
        
        # Send command to serial port if connected
        if serial_connection and serial_connection.is_open:
            try:
                command_str = str(data)
                serial_connection.write(command_str.encode('utf-8') + b'\n')
                print(f"[SERIAL] Sent: {command_str}")
            except Exception as e:
                print(f"[SERIAL] Error sending command: {e}")
                return jsonify({"status": "error", "error": str(e)}), 500
        
        return jsonify({"status": "command received", "command": data}), 200
    else:
        # GET request - return status
        return jsonify({"status": "ready", "message": "POST to this endpoint to send commands"}), 200


# Endpoint for serial communication with firmware
@app.route('/api/serial/send', methods=['GET', 'POST'])
def send_serial():
        data = request.get_json()
        serial_port = data.get('port') or os.environ.get('SERIAL_PORT', '/dev/ttyUSB0')
        # message = data.get('message', '')
        message = "moveto 90.0 90.0"
        if serial_connection and serial_connection.is_open:
            try:
                if message:
                    serial_connection.write(message.encode('utf-8') + b'\n')
                    print(f"[SERIAL] Sent: {message}")
                return jsonify({"status": "sent to serial", "data": data, "port": serial_connection.port}), 200
            except Exception as e:
                return jsonify({"status": "error", "error": str(e), "port": serial_port}), 500
        else:
            return jsonify({"status": "error", "error": "Serial port not connected", "port": serial_port}), 500


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
