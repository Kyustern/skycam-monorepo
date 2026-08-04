"""
Aircraft Data Service
Handles fetching aircraft data from OpenSky Network API.
Secrets are loaded from the project root secrets.json file.
"""
import json
import math
import os
import time
from typing import Optional, Dict, Any, List
import requests


class AircraftService:
    """Service for fetching aircraft data from OpenSky Network."""
    
    # Toulouse bounding box (default area)
    DEFAULT_LAT_MIN = 42.8448
    DEFAULT_LAT_MAX = 44.1972
    DEFAULT_LON_MIN = 0.6213
    DEFAULT_LON_MAX = 2.2152
    
    def __init__(self):
        """Initialize the service by loading secrets from file."""
        self._secrets = self._load_secrets()
        self._token_cache: Dict[str, Any] = {}
        self._token_expiry_seconds = 30 * 60  # 30 minutes
    
    def _load_secrets(self) -> Dict[str, Any]:
        """Load secrets from secrets.json file."""
        secrets_path = os.path.join("./secrets.json")
        
        if not os.path.exists(secrets_path):
            # Try alternative path
            secrets_path = os.path.join(os.path.dirname(__file__), "..", "secrets.json")
        
        if not os.path.exists(secrets_path):
            raise FileNotFoundError(
                f"secrets.json not found at {secrets_path}. "
                "Please ensure secrets.json exists at the project root."
            )
        
        with open(secrets_path, 'r') as f:
            return json.load(f)
    
    def _get_client_credentials(self) -> tuple:
        """Get OpenSky client credentials from secrets."""
        client_id = self._secrets.get("clientId")
        client_secret = self._secrets.get("clientSecret")
        
        if not client_id or not client_secret:
            raise ValueError("Missing clientId or clientSecret in secrets.json")
        
        return client_id, client_secret
    
    def _get_access_token(self) -> str:
        """Get or fetch a valid access token from OpenSky."""
        # Check cache
        cached = self._token_cache.get("access_token")
        cache_time = self._token_cache.get("cache_time")
        
        if cached and cache_time:
            if time.time() - cache_time < self._token_expiry_seconds:
                return cached
        
        # Fetch new token
        client_id, client_secret = self._get_client_credentials()
        
        auth_url = "https://auth.opensky-network.org/auth/realms/opensky-network/protocol/openid-connect/token"
        
        response = requests.post(
            auth_url,
            data={
                "grant_type": "client_credentials",
                "client_id": client_id,
                "client_secret": client_secret,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        
        response.raise_for_status()
        
        token_data = response.json()
        access_token = token_data.get("access_token")
        
        if not access_token:
            raise ValueError("Failed to obtain access token from OpenSky")
        
        # Update cache
        self._token_cache = {
            "access_token": access_token,
            "cache_time": time.time(),
        }
        
        return access_token
    
    def get_aircraft_in_area(
        self,
        lat_min: Optional[float] = None,
        lat_max: Optional[float] = None,
        lon_min: Optional[float] = None,
        lon_max: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Fetch aircraft data for a given bounding box.
        
        Args:
            lat_min: Minimum latitude (default: Toulouse area)
            lat_max: Maximum latitude (default: Toulouse area)
            lon_min: Minimum longitude (default: Toulouse area)
            lon_max: Maximum longitude (default: Toulouse area)
        
        Returns:
            Dictionary with aircraft data
        """
        # Use defaults if not provided
        lat_min = lat_min if lat_min is not None else self.DEFAULT_LAT_MIN
        lat_max = lat_max if lat_max is not None else self.DEFAULT_LAT_MAX
        lon_min = lon_min if lon_min is not None else self.DEFAULT_LON_MIN
        lon_max = lon_max if lon_max is not None else self.DEFAULT_LON_MAX
        
        access_token = self._get_access_token()
        
        url = "https://opensky-network.org/api/states/all"
        params = {
            "lamin": lat_min,
            "lamax": lat_max,
            "lomin": lon_min,
            "lomax": lon_max,
        }
        
        response = requests.get(
            url,
            headers={"Authorization": f"Bearer {access_token}"},
            params=params,
        )
        
        response.raise_for_status()
        return response.json()
    
    def get_aircraft_at_position(
        self,
        latitude: float,
        longitude: float,
        radius_km: float = 100.0,
    ) -> Dict[str, Any]:
        """
        Fetch aircraft data around a specific position.
        
        Note: OpenSky API doesn't support radius search directly,
        so we use a bounding box approximation.
        
        Args:
            latitude: Center latitude
            longitude: Center longitude
            radius_km: Search radius in kilometers (approximate)
        
        Returns:
            Dictionary with aircraft data
        """
        # Approximate degrees from km (1 degree latitude ~ 111 km)
        lat_delta = radius_km / 111.0
        # Longitude delta depends on latitude (1 degree ~ 111 km * cos(latitude))
        lon_delta = radius_km / (111.0 * max(0.001, abs(math.cos(math.radians(latitude)))))
        
        lat_min = latitude - lat_delta
        lat_max = latitude + lat_delta
        lon_min = longitude - lon_delta
        lon_max = longitude + lon_delta
        
        return self.get_aircraft_in_area(lat_min, lat_max, lon_min, lon_max)


# Global service instance
aircraft_service = AircraftService()
