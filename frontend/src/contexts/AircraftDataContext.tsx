import { createContext, useContext, useState, useEffect, useCallback, ReactNode } from "react";

// Re-export types for consistency
export type FlightState = {
    icao: string;
    callsign: string;
    origin_country: string;
    time_position: number;
    last_contact: number;
    longitude: number;
    latitude: number;
    baro_altitude: number;
    on_ground: boolean;
    velocity: number;
    true_track: number;
    vertical_rate: number;
    sensors: number[];
    geo_altitude: number;
    squawk: string;
    spi: boolean;
    position_source: number;
    category: number;
    baro_altitude_km: number;
};

export type Flights = Record<string, FlightState>;

type RawState = (string | number | boolean | number[])[];

type ADSBResponse = {
    time: number;
    states: RawState[] | null;
};

const TOULOUSE_LATMIN = 42.8448;
const TOULOUSE_LATMAX = 44.1972;
const TOULOUSE_LONMIN = 0.6213;
const TOULOUSE_LONMAX = 2.2152;

const parseRawState = (state: RawState): FlightState | null => {
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

const formatAircraftData = (apiResponse: ADSBResponse | null): Flights => {
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

// Use relative path for Vite proxy to forward to Flask server
// Vite config proxies /api/* to http://server:5000 (Docker service name)
const API_BASE = "/api";

// Fetch aircraft data from the server API
const fetchAircraftDataFromServer = async (
    position?: { latitude: number; longitude: number }
): Promise<ADSBResponse | null> => {
    try {
        let url = `${API_BASE}/aircraft`;
        
        const params = new URLSearchParams();
        
        if (position) {
            // Use position-based search with radius
            params.append("lat", position.latitude.toString());
            params.append("lon", position.longitude.toString());
            params.append("radius_km", "100");  // 100km radius
            url = `${API_BASE}/aircraft/position`;
        } else {
            // Use default Toulouse bounding box
            params.append("lat_min", TOULOUSE_LATMIN.toString());
            params.append("lat_max", TOULOUSE_LATMAX.toString());
            params.append("lon_min", TOULOUSE_LONMIN.toString());
            params.append("lon_max", TOULOUSE_LONMAX.toString());
        }
        
        const fullUrl = `${url}?${params.toString()}`;
        
        const response = await fetch(fullUrl, {
            headers: {
                "Content-Type": "application/json",
            },
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data: ADSBResponse = await response.json();
        return data;
    } catch (error) {
        console.error("Error fetching aircraft data from server:", error);
        return null;
    }
};

// Context type definition
interface AircraftDataContextType {
    token: string | null;
    formattedAircraftData: Flights;
    isLoading: boolean;
    error: string | null;
    refresh: (position?: { latitude: number; longitude: number }) => Promise<void>;
}

// Create the context with default values
const AircraftDataContext = createContext<AircraftDataContextType | undefined>(undefined);

// Props for the provider
interface AircraftDataProviderProps {
    children: ReactNode;
}

// Provider component
export const AircraftDataProvider = ({ children }: AircraftDataProviderProps) => {
    const [formattedAircraftData, setFormattedAircraftData] = useState<Flights>({});
    const [isLoading, setIsLoading] = useState<boolean>(true);
    const [error, setError] = useState<string | null>(null);

    const fetchAndUpdateData = useCallback(
        async (position?: { latitude: number; longitude: number }) => {
            setIsLoading(true);
            setError(null);

            try {
                const aircrafts = await fetchAircraftDataFromServer(position);
                const formattedData = formatAircraftData(aircrafts);
                setFormattedAircraftData(formattedData);
            } catch (err) {
                setError(err instanceof Error ? err.message : "Unknown error");
                console.error("Error in fetchAndUpdateData:", err);
            } finally {
                setIsLoading(false);
            }
        },
        []
    );

    // Initial data fetch on mount
    useEffect(() => {
        fetchAndUpdateData();
    }, [fetchAndUpdateData]);

    const value: AircraftDataContextType = {
        token: null, // Token is now managed server-side
        formattedAircraftData,
        isLoading,
        error,
        refresh: fetchAndUpdateData,
    };

    return (
        <AircraftDataContext.Provider value={value}>
            {children}
        </AircraftDataContext.Provider>
    );
};

// Custom hook to use the aircraft data context
export const useAircraftData = (): AircraftDataContextType => {
    const context = useContext(AircraftDataContext);
    if (context === undefined) {
        throw new Error("useAircraftData must be used within an AircraftDataProvider");
    }
    return context;
};
