import "bun";
import * as fs from "fs";

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

//Order in which we receive each data points from the opensky API
//Do not modify under any circumstances
const _STATE_KEYS: (keyof FlightState)[] = [
    "icao", "callsign", "origin_country", "time_position",
    "last_contact", "longitude", "latitude", "baro_altitude",
    "on_ground", "velocity", "true_track", "vertical_rate",
    "sensors", "geo_altitude", "squawk", "spi",
    "position_source", "category"
];

const parseRawState = (state: RawState) => {
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
            //Custom data
            baro_altitude_km: (baro_altitude as number) / 1000
        };

        return parsedState
    }
}


type RawState = (string | number | boolean | number[])[]

type ADSBResponse = {
    time: number,
    states: RawState[] | null
}

// export type FormattedAircraftData = {
//     [key: string]: FlightState;
// }


async function getAccessToken(): Promise<string> {
    const tokenFilePath = "token_cache.json";
    const TOKEN_EXPIRY_MINUTES = 30;

    // Try to read cached token
    try {
        if (fs.existsSync(tokenFilePath)) {
            const tokenData = JSON.parse(fs.readFileSync(tokenFilePath, "utf-8"));
            const creationDate = new Date(tokenData.creation_date);
            const now = new Date();

            // Calculate age in minutes
            const ageMinutes = (now.getTime() - creationDate.getTime()) / (1000 * 60);

            // If token is still valid, return it
            if (ageMinutes < TOKEN_EXPIRY_MINUTES && tokenData.access_token) {
                console.log("Using cached token");
                return tokenData.access_token;
            }
        }
    } catch (error) {
        console.warn("Error reading token cache, will fetch new token:", error);
    }

    // If no valid cached token, fetch new one
    let clientId, clientSecret;

    try {
        const secrets = JSON.parse(fs.readFileSync("secrets.json", "utf-8"));
        if (typeof secrets.clientId !== "string" || !secrets.clientId) {
            throw new Error("Client ID is not a valid string or is null");
        }
        if (typeof secrets.clientSecret !== "string" || !secrets.clientSecret) {
            throw new Error("Client Secret is not a valid string or is null");
        }
        clientId = secrets.clientId;
        clientSecret = secrets.clientSecret;
    } catch (error) {
        console.error("Error reading secrets.json or OpenSky credentials:", error);
        process.exit(1);
    }

    const url = "https://auth.opensky-network.org/auth/realms/opensky-network/protocol/openid-connect/token";
    const params = new URLSearchParams();
    params.append("grant_type", "client_credentials");
    params.append("client_id", clientId);
    params.append("client_secret", clientSecret);

    try {
        const requestStartTime = new Date(); // Capture timestamp when request is initiated
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

        // Store the new token with creation date
        const tokenCache = {
            access_token: data.access_token,
            creation_date: requestStartTime.toISOString()
        };

        fs.writeFileSync(tokenFilePath, JSON.stringify(tokenCache, null, 2));
        console.log("Stored new token in cache");

        return data.access_token;
    } catch (error) {
        console.error("Error fetching access token:", error);
        throw error;
    }
}

async function fetchAircraftData(token: string): Promise<ADSBResponse | null> {
    //Toulouse bounding box
    const latmax = 44.1972;
    const lonmax = 2.2152;
    const lonmin = 0.6213;
    const latmin = 42.8448;

    const url = `https://opensky-network.org/api/states/all?lamax=${latmax}&lomax=${lonmax}&lamin=${latmin}&lomin=${lonmin}`;

    try {
        const response = await fetch(url, {
            headers: {
                "Authorization": `Bearer ${token}`,
            },
        });
        if (!response.ok) {
            console.log(response);
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data: ADSBResponse = await response.json();
        return data;
    } catch (error) {
        console.error("Error fetching data:", error);
        return null;
    }
}

function formatAircraftData(apiResponse: ADSBResponse | null): Flights {
    const result: Flights = {};

    if (!apiResponse?.states) return result;

    const parsedStates = apiResponse.states.map((state) => parseRawState(state))

    
    parsedStates.forEach((pstate) => {
        if (pstate && !pstate.on_ground) {
            result[pstate.callsign.trim()] = pstate
        }
    })

    return result;
}

// Main function
async function main() {
    try {
        const token = await getAccessToken();
        const aircrafts = await fetchAircraftData(token);
        const formatedAircraftData = formatAircraftData(aircrafts);
        // Write to file if data is not null
        if (formatedAircraftData) {
            const outputPath = "src/assets/adsb_sample.json";
            fs.writeFileSync(outputPath, JSON.stringify(formatedAircraftData, null, 2));
            console.log(`Data written to ${outputPath}`);
        }
    } catch (error) {
        console.error("Error in main function:", error);
    }
}

main();
