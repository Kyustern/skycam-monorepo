import { useState, useEffect } from 'react'
import React from 'react'
import { useStore } from '../../store/useStore'
import { ObserverPositionForm } from './ObserverPositionForm'
import type { FlightState } from '../../scripts/scrap-airplane'
import type { OrbitControls as OrbitControlsImpl } from 'three-stdlib'

type SidebarProps = {
  controlsRef?: React.RefObject<OrbitControlsImpl | null>
}

export const Sidebar = ({ controlsRef }: SidebarProps) => {
  const searchRadius = useStore(state => state.searchRadius)
  const setSearchRadius = useStore(state => state.setSearchRadius)
  const [darkTheme, setDarkTheme] = useState(false)
  const darkness = useStore(state => state.darkness)
  const setDarkness = useStore(state => state.setDarkness)
  const setSelectionMode = useStore(state => state.setSelectionMode)
  const setSelectedFlight = useStore(state => state.setSelectedFlight)
  const selectedFlight = useStore(state => state.selectedFlight)
  const flights = useStore(state => state.flights)

  // Apply dark theme class to body
  useEffect(() => {
    if (darkTheme) {
      document.body.classList.add('dark-theme')
    } else {
      document.body.classList.remove('dark-theme')
    }
  }, [darkTheme])


  const handleFlightSelect = (flight: FlightState) => {
    setSelectedFlight(flight)
    setSelectionMode(null)
  }

  return (
    <div className="h-full sidebar text-sidebar-foreground p-4 z-10 col-span-1 dark-theme">
      <div className="flex justify-between items-center mb-4">
        <h1 className="text-xl font-bold">Earth Pointer</h1>
        <button
          onClick={() => setDarkTheme(!darkTheme)}
          className="accent text-sidebar-primary-foreground px-3 py-1 rounded-full text-sm hover:bg-opacity-80 transition-colors"
        >
          {darkTheme ? '☀️' : '🌙'}
        </button>
        <input
          type="range"
          min="0"
          max="1"
          step="0.01"
          value={darkness}
          onChange={(e) => setDarkness(parseFloat(e.target.value))}
          className="absolute top-4 left-4 z-10 w-64"
        />
      </div>

      <ObserverPositionForm />
      
      <div className="mt-6">
        <label className="block text-sm font-medium mb-2">Search Radius: {searchRadius} km</label>
        <input
          type="range"
          min="0"
          max="100"
          step="5"
          value={searchRadius}
          onChange={(e) => setSearchRadius(parseFloat(e.target.value))}
          className="w-full h-2 bg-sidebar-accent rounded-lg appearance-none cursor-pointer"
        />
        <div className="flex justify-between text-xs text-sidebar-foreground/60 mt-1">
          <span>1 km</span>
          <span>100 km</span>
        </div>
      </div>

      <div className="mt-8">
        
        {(!flights) ? (
          <div className="flex items-center justify-center py-4">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-sidebar-primary"></div>
            <span className="ml-2">Loading flights...</span>
          </div>
        ) : (
          <>
          {selectedFlight ? (
            <>
            <h2>
              {selectedFlight.callsign}
            </h2>
            <div className="text-sm text-gray-400">{selectedFlight.latitude.toFixed(4)}°N, {selectedFlight.longitude.toFixed(4)}°E</div>
            <div>
              {(selectedFlight.baro_altitude/ 1000).toFixed(3)} km
            </div>

            </>
          ) : (
            <h2>Select a flight to start</h2>
          )}
          <div className="space-y-2 overflow-y-auto max-h-[50vh] sidebar-accent rounded-lg p-2">
            {Object.values(flights).map((flight) => (
              <button
                key={flight.callsign}
                onClick={() => handleFlightSelect(flight)}
                className="w-full text-left p-2 rounded flight-item hover:bg-sidebar-primary hover:bg-opacity-20 transition-colors"
              >
                <div className="font-medium">{flight.callsign.trim()}</div>
                <div className="text-xs text-gray-500">Alt: {Math.round(flight.baro_altitude)}m</div>
              </button>
            ))}
          </div>
          </>
        )}

      </div>
    </div>
  )
}