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

// Raw state from ADS-B response
export type RawState = (string | number | boolean | number[])[];

// API response type
export type ADSBResponse = {
    time: number;
    states: RawState[] | null;
};

// Socket.IO connection states
export type SocketIOReadyState = 'connecting' | 'connected' | 'disconnected' | 'error';
