import { create } from 'zustand';
import { io, Socket } from 'socket.io-client';
import type { Flights, SocketIOReadyState, ADSBResponse } from '@/types/flightData';
import { formatAircraftData } from '@/utilities/flightDataUtils';
import { fetchNewFlights, type FetchNewFlightsParams } from '@/api/fetchNewFlights';

// Socket.IO endpoint - use relative path for Vite proxy
const SOCKET_IO_PATH = "/api/ws";

type WebSocketState = {
    socket: Socket | null;
    socketReadyState: SocketIOReadyState;
    error: string | null;
    flights: Flights;
    isLoading: boolean;
    fetchAndUpdateData: (params: FetchNewFlightsParams) => Promise<void>;
    reconnect: () => void;
    disconnect: () => void;
};

export const useWebSocketStore = create<WebSocketState>((set, get) => ({
    socket: null,
    socketReadyState: 'disconnected',
    error: null,
    flights: {},
    isLoading: false,

    fetchAndUpdateData: async (params) => {
        set({ isLoading: true, error: null });
        
        try {
            const formattedData = await fetchNewFlights(params);
            set({ flights: formattedData });
        } catch (err) {
            console.error("Error fetching aircraft data:", err);
            set({ error: err instanceof Error ? err.message : "Unknown error" });
        } finally {
            set({ isLoading: false });
        }
    },

    reconnect: () => {
        const { socket } = get();
        
        // If already connected, do nothing
        if (socket && socket.connected) {
            return;
        }

        set({ socketReadyState: 'connecting', error: null });

        try {
            // Disconnect existing socket if present
            if (socket) {
                socket.disconnect();
            }

            const newSocket = io("", {
                path: SOCKET_IO_PATH,
                reconnection: true,
                reconnectionAttempts: 10,
                reconnectionDelay: 1000,
                timeout: 20000
            });

            newSocket.on("connect", () => {
                console.log('Socket.IO connected at', Date.now());
                set({ socketReadyState: 'connected', socket: newSocket });
            });

            newSocket.on("disconnect", () => {
                console.log('Socket.IO disconnected', Date.now());
                set({ socketReadyState: 'disconnected' });
            });

            newSocket.on("connect_error", (err) => {
                console.error("Socket.IO connection error:", err);
                set({ socketReadyState: 'error', error: "Socket.IO connection error" });
            });

            // Handle aircraft data messages from websocket
            newSocket.on("aircraft_data", (data: unknown) => {
                try {
                    // const aircraftData = data as ADSBResponse;
                    const aircraftData = data as unknown as Flights;
                    // const formattedData = formatAircraftData(aircraftData);
                    set({ flights: aircraftData });
                } catch (err) {
                    console.error("Error parsing aircraft_data message:", err);
                    set({ error: "Failed to parse aircraft data" });
                }
            });

            newSocket.on("heartbeat", () => {
                console.log("heartbeat");
            });

        } catch (err) {
            console.error("Failed to create Socket.IO connection:", err);
            set({ socketReadyState: 'error', error: "Failed to create Socket.IO connection" });
        }
    },

    disconnect: () => {
        const { socket } = get();
        if (socket) {
            socket.disconnect();
            set({ socket: null, socketReadyState: 'disconnected' });
        }
    }
}));
