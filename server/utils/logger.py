"""
Logger utility for Turret server services.
Provides a consistent logging interface with service prefixes and timestamps.
"""
import time
from datetime import datetime


class ServiceLogger:
    """
    A logger class that formats log messages with a service prefix and timestamp.
    
    Usage:
        logger = ServiceLogger("KALMAN")
        logger.log("Starting prediction loop")
        logger.error("Error in prediction")
        logger.debug("Debug information")
        
    Output format:
        [KALMAN] [2026-08-19 14:30:45.123] Starting prediction loop
        [KALMAN] [2026-08-19 14:30:45.124] [ERROR] Error in prediction
        [KALMAN] [2026-08-19 14:30:45.125] [DEBUG] Debug information
    """
    
    # Available log modes and their prefixes
    MODE_PREFIXES = {
        "debug": "[DEBUG]",
        "info": "[INFO]",
        "warning": "[WARNING]",
        "error": "[ERROR]",
        "critical": "[CRITICAL]",
    }
    
    def __init__(self, service_name: str):
        """
        Initialize the logger with a service name prefix.
        
        Args:
            service_name: The name/identifier for the service (e.g., "KALMAN", "AIRCRAFT")
        """
        self.service_name = service_name.upper()
    
    def _get_timestamp(self) -> str:
        """Get current timestamp in human-readable format."""
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    
    def _format_message(self, message: str, mode: str = None) -> str:
        """
        Format a log message with service prefix, timestamp, and mode.
        
        Args:
            message: The log message
            mode: Optional mode (debug, info, warning, error, critical)
            
        Returns:
            Formatted log message string
        """
        timestamp = self._get_timestamp()
        mode_prefix = self.MODE_PREFIXES.get(mode.lower(), "") if mode else None
        
        # Build the formatted string: [SERVICE] [timestamp] [MODE] message
        parts = [f"[{self.service_name}]"]
        parts.append(f"[{timestamp}]")
        if mode_prefix:
            parts.append(mode_prefix)
        parts.append(str(message))
        
        return " ".join(parts)
    
    def log(self, message: str, mode: str = None):
        """
        Log a message with the service prefix and timestamp.
        
        Args:
            message: The message to log
            mode: Optional mode (debug, info, warning, error, critical)
        """
        formatted = self._format_message(message, mode)
        print(formatted)
    
    def debug(self, message: str):
        """Log a debug message."""
        self.log(message, mode="debug")
    
    def info(self, message: str):
        """Log an info message."""
        self.log(message, mode="info")
    
    def warning(self, message: str):
        """Log a warning message."""
        self.log(message, mode="warning")
    
    def error(self, message: str):
        """Log an error message."""
        self.log(message, mode="error")
    
    def critical(self, message: str):
        """Log a critical message."""
        self.log(message, mode="critical")


# Pre-configured logger instances for each service
# These can be imported and used directly by their respective services
kalman_logger = ServiceLogger("KALMAN")
aircraft_logger = ServiceLogger("AIRCRAFT")
serial_logger = ServiceLogger("SERIAL")
websocket_logger = ServiceLogger("WEBSOCKET")
turret_logger = ServiceLogger("TURRET")
server_logger = ServiceLogger("SERVER")


# Global default logger (can be used when service context is unknown)
default_logger = ServiceLogger("APP")


def get_logger(service_name: str) -> ServiceLogger:
    """
    Get or create a logger for a specific service.
    
    Args:
        service_name: The name of the service
        
    Returns:
        A ServiceLogger instance for the given service
    """
    return ServiceLogger(service_name)
