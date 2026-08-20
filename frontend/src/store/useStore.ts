import { create } from 'zustand'
import type { Flights, FlightState } from '../scripts/scrap-airplane'
import type { OrbitControls as OrbitControlsImpl } from 'three-stdlib'
import { focusCameraOnGPS } from '@/utilities/cameraUtils'
import { getSerialPorts, sendMovetoCommand } from '@/services/serialService';
import { computeAngles } from '@/utilities';

// In useStore.ts, replace the computeFlightsHash function with:

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

export type Coordinates = Pick<FlightState, "baro_altitude" | "latitude" |"longitude">

type StoreState = {
  observerPosition: Coordinates | null
  setObserverPosition: (position: Coordinates) => void
  searchRadius: number
  setSearchRadius: (radius: number) => void
  flights: Flights
  flightsHash: string
  setFlights: (flights: Flights) => void
  selectedFlight: FlightState | null
  setSelectedFlight: (flight: FlightState) => void
  selectionMode: 'airplane' | 'satellite' | 'spatial' | null
  setSelectionMode: (mode: 'airplane' | 'satellite' | 'spatial' | null) => void
  darkness: number
  setDarkness: (darkness: number) => void
  controls: OrbitControlsImpl | null,
  setControls: (controls: OrbitControlsImpl | null) => void
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
  flights: null,
  flightsHash: "",
  setFlights: (newFlights: Flights | null) => {
    const newHash = computeFlightsHash(newFlights)
    const currentSelectedFlight = get().selectedFlight
    const newSelectedFlight = currentSelectedFlight?.callsign ? newFlights[currentSelectedFlight.callsign.trim().toLocaleUpperCase()] : null

    // if (newSelectedFlight && observerPosition) {
    //   const angles = computeAngles(observerPosition, newSelectedFlight)
    //   console.log('LTES - angles', angles);
    //   sendMovetoCommand({
    //     azimuth: angles.signedAzimuth,
    //     elevation: angles.verticalAngle
    //   })
    // }
    
    set({
      flights: newFlights, 
      flightsHash: newHash, 
      selectedFlight: newSelectedFlight
     })
  },
  selectedFlight: null,
  setSelectedFlight: (newSelectedFlight) => {
    const cameraControls = get().controls
    if (cameraControls) {
      focusCameraOnGPS(cameraControls, newSelectedFlight.latitude, newSelectedFlight.longitude, newSelectedFlight.baro_altitude/1000)

    }
    set({ selectedFlight: newSelectedFlight })
  },
  selectionMode: null,
  setSelectionMode: (mode) => set({ selectionMode: mode }),
  darkness: 0.5,
  setDarkness: (darkness) => set({darkness}),
  controls: null,
  setControls: (controls) => set({controls})
}))
