import { useState, useEffect } from 'react'
import React from 'react'
import { useStore } from '../../store/useStore'
import { ObserverPositionForm } from './ObserverPositionForm'
import type { FlightState } from '../../scripts/scrap-airplane'
import type { OrbitControls as OrbitControlsImpl } from 'three-stdlib'
import { focusCameraOnGPS, animateCameraFocus } from '../../utilities/cameraUtils'

type SidebarProps = {
  controlsRef?: React.RefObject<OrbitControlsImpl | null>
}

export const Sidebar = ({ controlsRef }: SidebarProps) => {
  const observerPosition = useStore(state => state.observerPosition)
  const [darkTheme, setDarkTheme] = useState(false)
  const darkness = useStore(state => state.darkness)
  const setDarkness = useStore(state => state.setDarkness)
  const setSelectionMode = useStore(state => state.setSelectionMode)
  const setSelectedFlight = useStore(state => state.setSelectedFlight)
  const flights = useStore(state => state.flights)

  const handleFocusPosition = () => {
    if (controlsRef?.current && observerPosition) {
      const targetPosition = focusCameraOnGPS(
        controlsRef.current,
        observerPosition.latitude,
        observerPosition.longitude,
        observerPosition.baro_altitude
      )
      animateCameraFocus(controlsRef.current, targetPosition)
    }
  }

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

      <ObserverPositionForm onFocusPosition={handleFocusPosition} />

      <div className="mt-8">
        <h2 className="text-lg font-semibold mb-2">Flights</h2>
        
        {(!flights) ? (
          <div className="flex items-center justify-center py-4">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-sidebar-primary"></div>
            <span className="ml-2">Loading flights...</span>
          </div>
        ) : (
          <div className="space-y-2 overflow-y-auto max-h-[50vh] sidebar-accent rounded-lg p-2">
            {Object.values(flights).map((flight) => (
              <button
                key={flight.callsign}
                onClick={() => handleFlightSelect(flight)}
                className="w-full text-left p-2 rounded flight-item hover:bg-sidebar-primary hover:bg-opacity-20 transition-colors"
              >
                <div className="font-medium">{flight.callsign.trim()}</div>
                <div className="text-sm text-gray-400">{flight.latitude.toFixed(4)}°N, {flight.longitude.toFixed(4)}°E</div>
                <div className="text-xs text-gray-500">Alt: {Math.round(flight.baro_altitude)}m</div>
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}