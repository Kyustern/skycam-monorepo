import { create } from 'zustand'
import type { OrbitControls as OrbitControlsImpl } from 'three-stdlib'
import { focusCameraOnGPS } from '@/utilities/cameraUtils'
import { Flights } from '@/types/flightData';
import { io, Socket } from 'socket.io-client';
import type { SocketIOReadyState } from '@/types/flightData';
import { fetchNewFlights, type FetchNewFlightsParams } from '@/api/fetchNewFlights';

// Socket.IO endpoint - use relative path for Vite proxy
const SOCKET_IO_PATH = "/api/ws";

function computeFlightsHash(flights: Flights | null): string {
  if (!flights) return ''

  // Custom replacer to preserve full precision for all numbers
  const replacer = (key: string, value: any): any => {
    if (typeof value === 'number') {
      // Use toFixed with enough precision for coordinates/altitude
      // 10 decimal places handles most GPS precision needs
      return Number(value.toFixed(10))
    }
    return value
  }

  const str = JSON.stringify(flights, (k, v) => {
    if (typeof v === 'number') return Number(v.toFixed(10))
    return v
  })

  // Simple DJB2 hash algorithm
  let hash = 5381
  for (let i = 0; i < str.length; i++) {
    hash = ((hash << 5) + hash) + str.charCodeAt(i)
    hash |= 0 // Convert to 32-bit integer
  }

  return (hash >>> 0).toString(16)
}

export type Coordinates = Pick<import('@/types/flightData').FlightState, "baro_altitude" | "latitude" | "longitude">

type StoreState = {
  observerPosition: Coordinates | null
  setObserverPosition: (position: Coordinates) => void
  searchRadius: number
  setSearchRadius: (radius: number) => void
  flights: Flights
  predictions: Flights
  flightsHash: string
  setFlights: (flights: Flights) => void
  setPredictions: (flights: Flights) => void
  selectedFlight: import('@/types/flightData').FlightState | null
  setSelectedFlight: (flight: import('@/types/flightData').FlightState) => void
  selectionMode: 'airplane' | 'satellite' | 'spatial' | null
  setSelectionMode: (mode: 'airplane' | 'satellite' | 'spatial' | null) => void
  darkness: number
  setDarkness: (darkness: number) => void
  controls: OrbitControlsImpl | null,
  setControls: (controls: OrbitControlsImpl | null) => void
  
  // WebSocket state
  socket: Socket | null
  socketReadyState: SocketIOReadyState
  wsError: string | null
  isLoading: boolean
  fetchAndUpdateData: (params: FetchNewFlightsParams) => Promise<void>
  reconnect: () => void
  disconnect: () => void
}

// Default coordinates for Toulouse (from the original secrets.json DEFAULT_LOCATION)
const DEFAULT_OBSERVER_POSITION: Coordinates = {
  latitude: 43.633796109606884,
  longitude: 1.436305522994527,
  baro_altitude: 160,
}

export const useStore = create<StoreState>((set, get) => ({
  observerPosition: DEFAULT_OBSERVER_POSITION,
  setObserverPosition: (position) => set({ observerPosition: position }),
  searchRadius: 20,
  setSearchRadius: (radius) => set({ searchRadius: radius }),
  flights: {},
  predictions: {},
  flightsHash: "",
  setFlights: (newFlights: Flights | null) => {
    const newHash = computeFlightsHash(newFlights)
    const currentSelectedFlight = get().selectedFlight
    const newSelectedFlight = currentSelectedFlight?.callsign ? newFlights[currentSelectedFlight.callsign.trim().toLocaleUpperCase()] : null

    set({
      flights: newFlights,
      flightsHash: newHash,
      selectedFlight: newSelectedFlight
    })
  },
  setPredictions: (newPredictions: Flights | null) => {
    set({
      predictions: newPredictions
    })

  },
  selectedFlight: null,
  setSelectedFlight: (newSelectedFlight) => {
    const cameraControls = get().controls
    if (cameraControls) {
      focusCameraOnGPS(cameraControls, newSelectedFlight.latitude, newSelectedFlight.longitude, newSelectedFlight.baro_altitude / 1000)

    }
    set({ selectedFlight: newSelectedFlight })
  },
  selectionMode: null,
  setSelectionMode: (mode) => set({ selectionMode: mode }),
  darkness: 0.5,
  setDarkness: (darkness) => set({ darkness }),
  controls: null,
  setControls: (controls) => set({ controls }),

  // WebSocket state
  socket: null,
  socketReadyState: 'disconnected',
  wsError: null,
  isLoading: false,

  fetchAndUpdateData: async (params) => {
    set({ isLoading: true, wsError: null });
    
    try {
      const formattedData = await fetchNewFlights(params);
      get().setFlights(formattedData);
    } catch (err) {
      console.error("Error fetching aircraft data:", err);
      set({ wsError: err instanceof Error ? err.message : "Unknown error" });
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

    set({ socketReadyState: 'connecting', wsError: null });

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
        set({ socketReadyState: 'error', wsError: "Socket.IO connection error" });
      });

      // Handle aircraft data messages from websocket
      newSocket.on("aircraft_data", (data: unknown) => {
        try {
          const aircraftData = data as unknown as Flights;
          get().setFlights(aircraftData);
        } catch (err) {
          console.error("Error parsing aircraft_data message:", err);
          set({ wsError: "Failed to parse aircraft data" });
        }
      });

      newSocket.on("prediction_data", (data: unknown) => {
        try {
          const predictionData = data as unknown as Flights;
          console.log('LTES - predictionData', predictionData);
          get().setPredictions(predictionData);
        } catch (err) {
          console.error("Error parsing prediction_data message:", err);
          set({ wsError: "Failed to parse prediction data" });
        }
      });

      newSocket.on("heartbeat", () => {
        console.log("heartbeat");
      });

    } catch (err) {
      console.error("Failed to create Socket.IO connection:", err);
      set({ socketReadyState: 'error', wsError: "Failed to create Socket.IO connection" });
    }
  },

  disconnect: () => {
    const { socket } = get();
    if (socket) {
      socket.disconnect();
      set({ socket: null, socketReadyState: 'disconnected' });
    }
  }
}))


