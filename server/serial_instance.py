"""
Centralized serial connection instance for the Turret server.

This module provides a global pyserial connection that can be imported
and used across different parts of the application without circular imports.

Usage:
    from serial_instance import init_serial, get_serial, send_command

    init_serial()               # once, at startup
    conn = get_serial()         # the pyserial.Serial instance, or None
    send_command("moveto 1.00 2.00")
"""
import os
import threading
import time

import serial
import serial.tools.list_ports

from utils.logger import serial_logger

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
        serial_logger.error(f"Error listing serial ports: {e}")
        return []


def init_serial(start_reader=True):
    """
    Initialize the serial connection.

    Port and baudrate default to the SERIAL_PORT / SERIAL_RATE environment
    variables (falling back to /dev/ttyUSB0 and 9600).

    Args:
        start_reader: Whether to start the background reader thread

    Returns:
        True if the connection was established, False otherwise
    """
    global serial_connection, reader_thread

    serial_port = os.environ.get('SERIAL_PORT', '/dev/ttyUSB0')
    serial_rate = os.environ.get('SERIAL_RATE', '9600')

    # Close existing connection if open
    if serial_connection and serial_connection.is_open:
        try:
            serial_connection.close()
            serial_logger.info("Closed existing serial connection")
        except Exception as e:
            serial_logger.error(f"Error closing existing serial port: {e}")
        serial_connection = None

    # Clear shutdown flag for new connection
    shutdown_flag.clear()

    try:
        serial_connection = serial.Serial(
            port=serial_port,
            baudrate=serial_rate,
            timeout=1
        )
        serial_logger.info(f"Connected to {serial_port} at {serial_rate} baud")

        if start_reader:
            reader_thread = threading.Thread(target=read_serial, daemon=True)
            reader_thread.start()
        return True
    except Exception as e:
        serial_logger.error(f"Error connecting to {serial_port}: {e}")
        serial_connection = None
        return False


def get_serial():
    """
    Get the initialized serial connection.

    Returns:
        The pyserial.Serial instance, or None if not connected
    """
    return serial_connection


def is_connected():
    """Return True if the serial connection is open."""
    return serial_connection is not None and serial_connection.is_open


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
            serial_logger.warning("Serial connection lost. A new command will trigger reconnection.")
            break
        except Exception as e:
            serial_logger.error(f"Unexpected error: {e}")
            break


def send_command(command_str):
    """
    Send a command string to the serial port, reconnecting if needed.

    Args:
        command_str: The command to send (newline is appended)

    Returns:
        True if the command was sent, False otherwise
    """
    global serial_connection
    serial_logger.debug(f"Sending command, connection: {serial_connection}")

    # Attempt to reconnect if connection is down
    if serial_connection is None or not serial_connection.is_open:
        serial_logger.info("No active serial connection, attempting to reconnect...")
        init_serial()
        time.sleep(0.1)  # Small delay to allow connection to establish

    if serial_connection and serial_connection.is_open:
        try:
            serial_logger.debug(f"Command to send: {command_str}")
            serial_connection.write(command_str.encode('utf-8') + b'\n')
            serial_logger.info(f"Sent: {command_str}")
            return True
        except Exception as e:
            serial_logger.error(f"Error sending command: {e}")
            # Mark connection as bad so next attempt will reconnect
            try:
                serial_connection.close()
            except:
                pass
            serial_connection = None
            return False
    else:
        serial_logger.error("Serial port not connected after reconnection attempt")
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
    # But don't try to join if we're the reader thread ourselves (avoid deadlock)
    if reader_thread and reader_thread.is_alive() and reader_thread is not threading.current_thread():
        reader_thread.join(timeout=2.0)
        if reader_thread.is_alive():
            serial_logger.warning("Reader thread did not stop gracefully")
        else:
            serial_logger.info("Reader thread stopped")
