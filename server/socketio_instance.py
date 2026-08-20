"""
Centralized SocketIO instance for the Turret server.

This module provides a global SocketIO instance that can be imported
and used across different parts of the application without circular imports.
"""
from flask_socketio import SocketIO

# Global SocketIO instance
socketio = None


def init_socketio(app, cors_allowed_origins="*", async_mode='eventlet', path="/api/ws"):
    """
    Initialize the SocketIO instance with the given Flask app.
    
    Args:
        app: Flask application instance
        cors_allowed_origins: CORS allowed origins (default: "*")
        async_mode: Async mode for SocketIO (default: 'eventlet')
        path: WebSocket path (default: "/api/ws")
    
    Returns:
        The initialized SocketIO instance
    """
    global socketio
    socketio = SocketIO(
        app,
        cors_allowed_origins=cors_allowed_origins,
        async_mode=async_mode,
        path=path
    )
    return socketio


def get_socketio():
    """
    Get the initialized SocketIO instance.
    
    Returns:
        The SocketIO instance, or None if not initialized
    """
    return socketio
