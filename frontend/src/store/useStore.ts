import { create } from 'zustand'
import type { Flights, FlightState } from '../scripts/scrap-airplane'
import type { OrbitControls as OrbitControlsImpl } from 'three-stdlib'

// type Coordinates = {
//   lat: number
//   lon: number
//   baro_alt: number
// }

type Coordinates = Pick<FlightState, "baro_altitude" | "latitude" |"longitude">

type StoreState = {
  observerPosition: Coordinates | null
  setObserverPosition: (position: Coordinates) => void
  flights: Flights
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

const DEFAULT_OBSERVER_POSITION: Coordinates = {
  latitude: 45.6791709420156,
  longitude: -0.5932216931856488,
  baro_altitude: 50,
}

export const useStore = create<StoreState>((set) => ({
  observerPosition: DEFAULT_OBSERVER_POSITION,
  setObserverPosition: (position) => set({ observerPosition: position }),
  flights: null,
  setFlights: (flights) => set({flights: flights}),
  selectedFlight: null,
  setSelectedFlight: (flight) => set({ selectedFlight: flight }),
  selectionMode: null,
  setSelectionMode: (mode) => set({ selectionMode: mode }),
  darkness: 0.5,
  setDarkness: (darkness) => set({darkness}),
  controls: null,
  setControls: (controls) => set({controls})
}))
