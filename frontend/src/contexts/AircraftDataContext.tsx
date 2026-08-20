import { Coordinates } from "@/store/useStore";
import { createContext, useContext, useState, useEffect, useCallback, ReactNode, useRef } from "react";
import { io, Socket } from "socket.io-client";

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
    params?: {
        observer_position: Coordinates,
        radius: number
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
};

// Socket.IO connection states
type SocketIOReadyState = 'connecting' | 'connected' | 'disconnected' | 'error';

// Context type definition
interface AircraftDataContextType {
    token: string | null;
    formattedAircraftData: Flights;
    isLoading: boolean;
    error: string | null;
    refresh: (params: {
        observer_position: Coordinates,
        radius: number
    }) => Promise<void>;
    socketReadyState: SocketIOReadyState;
    reconnect: () => void;
}

// Create the context with default values
const AircraftDataContext = createContext<AircraftDataContextType | undefined>(undefined);

// Props for the provider
interface AircraftDataProviderProps {
    children: ReactNode;
}

// Socket.IO endpoint - use relative path for Vite proxy
const SOCKET_IO_PATH = "/api/ws";

// Provider component
export const AircraftDataProvider = ({ children }: AircraftDataProviderProps) => {
    const [formattedAircraftData, setFormattedAircraftData] = useState<Flights>({});
    const [isLoading, setIsLoading] = useState<boolean>(true);
    const [error, setError] = useState<string | null>(null);
    const [socketReadyState, setSocketReadyState] = useState<SocketIOReadyState>('disconnected');

    // Store Socket.IO instance in a ref
    const socketRef = useRef<Socket | null>(null);
    const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

    // Handle incoming Socket.IO messages
    const handleSocketMessage = useCallback((data: ADSBResponse) => {
        try {
            const formattedData = formatAircraftData(data);
            setFormattedAircraftData(prev => ({ ...prev, ...formattedData }));
        } catch (err) {
            console.error("Error parsing Socket.IO message:", err);
            setError("Failed to parse Socket.IO data");
        }
    }, []);

    // Reconnection logic with exponential backoff
    const reconnect = useCallback(() => {
        if (socketRef.current && socketRef.current.connected) {
            return;
        }

        // Clear any existing reconnection timeout
        if (reconnectTimeoutRef.current) {
            clearTimeout(reconnectTimeoutRef.current);
        }

        setSocketReadyState('connecting');
        setError(null);

        try {
            // Disconnect existing socket if present
            if (socketRef.current) {
                socketRef.current.disconnect();
                socketRef.current = null;
            }

            const socket = io("", {
                path: SOCKET_IO_PATH,
                reconnection: true,        // Let Socket.IO handle reconnects
                reconnectionAttempts: 10,  // Retry up to 10 times
                reconnectionDelay: 1000,  // Start with 1s, then exponential backoff
                timeout: 20000            // Wait 20s before considering disconnected
            });

            socket.on("connect", () => {
                setSocketReadyState('connected');
                console.log('Socket.IO connected at ');
                console.log(Date.now())
            });

            socket.on("disconnect", () => {
                setSocketReadyState('disconnected');
                console.log('Socket.IO disconnected');
                console.log(Date.now())
                // Attempt to reconnect after delay
                // reconnectTimeoutRef.current = setTimeout(() => {
                //     reconnect();
                // }, 5000); // 5 second delay before reconnect
            });


            socket.on("connect_error", (err) => {
                setSocketReadyState('error');
                setError("Socket.IO connection error");
                console.error("Socket.IO connection error:", err);
            });

            socket.on("aircraft_data", (_aircraft_data) => {
                const aircraft_data = _aircraft_data as unknown as Flights
            });
            socket.on("heartbeat_predictions", () => {
                console.log("heartbeat")

            });

            socketRef.current = socket;
        } catch (err) {
            console.error("Failed to create Socket.IO connection:", err);
            setSocketReadyState('error');
            setError("Failed to create Socket.IO connection");
        }
    }, [handleSocketMessage]);

    const fetchAndUpdateData = useCallback(
        async (params: {
            observer_position: Coordinates,
            radius: number
        }) => {
            setIsLoading(true);
            setError(null);

            try {
                const aircrafts = await fetchAircraftDataFromServer(params);
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

    // Initialize Socket.IO connection on mount
    useEffect(() => {
        const asyncEffect = async () => {
            // Fetch initial data via REST API
            // await fetchAndUpdateData();

            // Connect Socket.IO for real-time updates
            reconnect();

            return () => {
                // Cleanup Socket.IO connection
                if (reconnectTimeoutRef.current) {
                    clearTimeout(reconnectTimeoutRef.current);
                }
                if (socketRef.current) {
                    socketRef.current.disconnect();
                    socketRef.current = null;
                }
            };
        }

        asyncEffect()

    }, [fetchAndUpdateData, reconnect]);

    const value: AircraftDataContextType = {
        token: null,
        formattedAircraftData,
        isLoading,
        error,
        refresh: fetchAndUpdateData,
        socketReadyState,
        reconnect,
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
