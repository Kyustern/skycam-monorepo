import { useState, useEffect, useCallback } from "react";

// Re-export types from the original script
export type FlightState = {
    icao: string,
    callsign: string,
    origin_country: string,
    time_position: number,
    last_contact: number,
    longitude: number,
    latitude: number,
    baro_altitude: number,
    on_ground: boolean,
    velocity: number,
    true_track: number,
    vertical_rate: number,
    sensors: number[],
    geo_altitude: number,
    squawk: string,
    spi: boolean,
    position_source: number,
    category: number,
    baro_altitude_km: number
}

export type Flights = Record<string, FlightState>

type RawState = (string | number | boolean | number[])[]

type ADSBResponse = {
    time: number,
    states: RawState[] | null
}

type TokenCache = {
    access_token: string;
    creation_date: string;
}

type Secrets = {
    clientId: string;
    clientSecret: string;
}

const TOKEN_EXPIRY_MINUTES = 30;

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
            category
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
            baro_altitude_km: (baro_altitude as number) / 1000
        };

        return parsedState;
    }
    return null;
}

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

const fetchAccessToken = async (
    clientId: string,
    clientSecret: string
): Promise<string> => {
    const url = "/auth.opensky-network.org/auth/realms/opensky-network/protocol/openid-connect/token";
    const params = new URLSearchParams();
    params.append("grant_type", "client_credentials");
    params.append("client_id", clientId);
    params.append("client_secret", clientSecret);

    const response = await fetch(url, {
        method: "POST",
        headers: {
            "Content-Type": "application/x-www-form-urlencoded",
        },
        body: params,
    });

    if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();
    return data.access_token;
};

const TOULOUSE_LATMIN = 42.8448;
const TOULOUSE_LATMAX = 44.1972;
const TOULOUSE_LONMIN = 0.6213;
const TOULOUSE_LONMAX = 2.2152;

const BOUNDING_BOX_HEIGHT = TOULOUSE_LATMAX - TOULOUSE_LATMIN;
const BOUNDING_BOX_WIDTH = TOULOUSE_LONMAX - TOULOUSE_LONMIN;

const fetchAircraftData = async (token: string, position?: { latitude: number; longitude: number }): Promise<ADSBResponse | null> => {
    console.log("position", position);
    let latmax = TOULOUSE_LATMAX;
    let lonmax = TOULOUSE_LONMAX;
    let lonmin = TOULOUSE_LONMIN;
    let latmin = TOULOUSE_LATMIN;

    if (position) {
        latmin = position.latitude - (BOUNDING_BOX_HEIGHT / 2);
        latmax = position.latitude + (BOUNDING_BOX_HEIGHT / 2);
        lonmin = position.longitude - (BOUNDING_BOX_WIDTH / 2);
        lonmax = position.longitude + (BOUNDING_BOX_WIDTH / 2);
    }

    const url = `/opensky-network.org/api/states/all?lamax=${latmax}&lomax=${lonmax}&lamin=${latmin}&lomin=${lonmin}`;

    try {
        const response = await fetch(url, {
            headers: {
                "Authorization": `Bearer ${token}`,
            },
        });
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data: ADSBResponse = await response.json();
        return data;
    } catch (error) {
        console.error("Error fetching data:", error);
        return null;
    }
};

interface UseAircraftDataResult {
    token: string | null;
    formattedAircraftData: Flights;
    isLoading: boolean;
    error: string | null;
    refresh: (position?: { latitude: number; longitude: number }) => Promise<void>;
}

interface UseAircraftDataParams {
    observerPosition?: { latitude: number; longitude: number };
}

export function useAircraftData(params?: UseAircraftDataParams): UseAircraftDataResult {
    const { observerPosition } = params || {};
    const [secrets, setSecrets] = useState<Secrets | null>(null);
    const [secretsError, setSecretsError] = useState<string | null>(null);
    const [tokenCache, setTokenCache] = useState<TokenCache | null>(null);
    const [formattedAircraftData, setFormattedAircraftData] = useState<Flights>({});
    const [isLoading, setIsLoading] = useState<boolean>(true);
    const [error, setError] = useState<string | null>(null);

    // Load secrets from secrets.json on mount
    useEffect(() => {
        const loadSecrets = async () => {
            try {
                const response = await fetch("/secrets.json?v=" + Date.now());
                if (!response.ok) {
                    throw new Error(`Failed to load secrets.json: ${response.status}`);
                }
                const data: Secrets = await response.json();
                
                if (typeof data.clientId !== "string" || !data.clientId) {
                    throw new Error("Client ID is not a valid string or is null");
                }
                if (typeof data.clientSecret !== "string" || !data.clientSecret) {
                    throw new Error("Client Secret is not a valid string or is null");
                }
                
                setSecrets(data);
            } catch (err) {
                setSecretsError(err instanceof Error ? err.message : "Unknown error loading secrets");
                console.error("Error loading secrets.json:", err);
            }
        };
        
        loadSecrets();
    }, []);

    const getToken = useCallback(async (): Promise<string> => {
        if (!secrets) {
            throw new Error("Secrets not loaded yet");
        }

        const now = new Date();

        // Check if we have a cached token that's still valid
        if (tokenCache) {
            const creationDate = new Date(tokenCache.creation_date);
            const ageMinutes = (now.getTime() - creationDate.getTime()) / (1000 * 60);
            
            if (ageMinutes < TOKEN_EXPIRY_MINUTES && tokenCache.access_token) {
                return tokenCache.access_token;
            }
        }

        // Fetch new token
        const newToken = await fetchAccessToken(secrets.clientId, secrets.clientSecret);
        
        // Update cache
        setTokenCache({
            access_token: newToken,
            creation_date: now.toISOString()
        });
        
        return newToken;
    }, [secrets, tokenCache]);

    const fetchAndUpdateData = useCallback(async (position?: { latitude: number; longitude: number }) => {
        if (!secrets) {
            setError("Secrets not loaded");
            return;
        }

        setIsLoading(true);
        setError(null);

        try {
            const token = await getToken();
            const aircrafts = await fetchAircraftData(token, position);
            const formattedData = formatAircraftData(aircrafts);
            setFormattedAircraftData(formattedData);
        } catch (err) {
            setError(err instanceof Error ? err.message : "Unknown error");
            console.error("Error in fetchAndUpdateData:", err);
        } finally {
            setIsLoading(false);
        }
    }, [getToken, secrets]);

    // Fetch data whenever secrets are loaded
    useEffect(() => {
        if (secrets && !secretsError) {
            fetchAndUpdateData(observerPosition);
        }
    }, [secrets, secretsError, fetchAndUpdateData]);

    return {
        token: tokenCache?.access_token ?? null,
        formattedAircraftData,
        isLoading: isLoading || secrets === null,
        error: error || secretsError,
        refresh: fetchAndUpdateData,
    };
}
