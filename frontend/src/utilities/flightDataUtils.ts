import type { FlightState, Flights, ADSBResponse, RawState } from '@/types/flightData';

/**
 * Parse raw ADS-B state array into a FlightState object
 */
export const parseRawState = (state: RawState): FlightState | null => {
    if (Array.isArray(state)) {
        const [
            icao,
            callsign,
            origin_country,
            time_position,
            last_contact,
            longitude,
            latitude,
            baro_altitude,
            on_ground,
            velocity,
            true_track,
            vertical_rate,
            sensors,
            geo_altitude,
            squawk,
            spi,
            position_source,
            category,
        ] = state;

        const parsedState: FlightState = {
            icao: icao as string,
            callsign: callsign as string,
            origin_country: origin_country as string,
            time_position: time_position as number,
            last_contact: last_contact as number,
            longitude: longitude as number,
            latitude: latitude as number,
            baro_altitude: baro_altitude as number,
            on_ground: on_ground as boolean,
            velocity: velocity as number,
            true_track: true_track as number,
            vertical_rate: vertical_rate as number,
            sensors: sensors as number[],
            geo_altitude: geo_altitude as number,
            squawk: squawk as string,
            spi: spi as boolean,
            position_source: position_source as number,
            category: category as number,
            baro_altitude_km: (baro_altitude as number) / 1000,
        };

        return parsedState;
    }
    return null;
};

/**
 * Format ADS-B API response into Flights record
 * Filters out aircraft that are on the ground
 */
export const formatAircraftData = (apiResponse: ADSBResponse | null): Flights => {
    const result: Flights = {};

    if (!apiResponse?.states) return result;

    const parsedStates = apiResponse.states.map((state) => parseRawState(state));

    parsedStates.forEach((pstate) => {
        if (pstate && !pstate.on_ground) {
            result[pstate.callsign.trim()] = pstate;
        }
    });

    return result;
};

// API base path - use relative path for Vite proxy
const API_BASE = "/api";

/**
 * Fetch aircraft data from the server API
 */
export const fetchAircraftDataFromServer = async (
    params?: {
        observer_position: { latitude: number; longitude: number; baro_altitude: number };
        radius: number;
    }
): Promise<ADSBResponse | null> => {
    try {
        const url = `${API_BASE}/aircraft/position`;

        if (params?.observer_position) {
            // Use position-based search with POST request
            const response = await fetch(url, {
                method: 'POST',
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({
                    lat: params.observer_position.latitude,
                    lon: params.observer_position.longitude,
                    radius_km: params.radius || 100
                })
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data: ADSBResponse = await response.json();
            return data;
        }
    } catch (error) {
        console.error("Error fetching aircraft data from server:", error);
        return null;
    }
    return null;
};
