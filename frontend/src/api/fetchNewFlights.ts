import type { ADSBResponse } from '@/types/flightData';
import { formatAircraftData } from '@/utilities/flightDataUtils';
import type { Flights } from '@/types/flightData';

export type FetchNewFlightsParams = {
    observer_position: { latitude: number; longitude: number; baro_altitude: number };
    radius: number;
};

/**
 * Fetch new flight data from the API and return formatted flights
 */
export async function fetchNewFlights(params: FetchNewFlightsParams): Promise<Flights> {
    try {
        const response = await fetch("/api/aircraft/position", {
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
        return formatAircraftData(data);
    } catch (err) {
        console.error("Error fetching aircraft data:", err);
        throw err;
    }
}
