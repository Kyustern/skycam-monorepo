import { useState, useEffect } from 'react'
import { useStore } from '../../store/useStore'
import { FlightSidebar } from './FlightSidebar'

export const Sidebar = () => {
  const observerPosition = useStore(state => state.observerPosition)
  const [latitude, setLatitude] = useState(observerPosition.latitude)
  const [longitude, setLongitude] = useState(observerPosition.longitude)
  const [baroalt, setBaroalt] = useState(observerPosition.baro_altitude)
  const [darkTheme, setDarkTheme] = useState(false)
  const darkness = useStore(state => state.darkness)
  const setDarkness = useStore(state => state.setDarkness)
  const setObserverPosition = useStore(state => state.setObserverPosition)
  const setSelectionMode = useStore(state => state.setSelectionMode)
  const [isValid, setIsValid] = useState(true)

  // Apply dark theme class to body
  useEffect(() => {
    if (darkTheme) {
      document.body.classList.add('dark-theme')
    } else {
      document.body.classList.remove('dark-theme')
    }
  }, [darkTheme])


  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()

    const lat = latitude
    const lon = longitude
    const baro_alt = baroalt

    // Basic validation
    if (isNaN(lat) || isNaN(lon) || lat < -90 || lat > 90 || lon < -180 || lon > 180) {
      setIsValid(false)
      return
    }

    setIsValid(true)
    setObserverPosition({ latitude: lat, longitude: lon, baro_altitude: baro_alt })
  }

  const handleModeSelect = (mode: 'airplane' | 'satellite' | 'spatial') => {
    setSelectionMode(mode)
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

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label htmlFor="latitude" className="block text-sm font-medium mb-1">
            Latitude
          </label>
          <input
            type="text"
            id="latitude"
            value={latitude}
            onChange={(e) => setLatitude(parseFloat(e.target.value))}
            className={`w-full px-3 py-2 border rounded-md ${!isValid ? 'border-red-500' : 'border-gray-300'}`}
            placeholder="e.g. 43.6047"
          />
        </div>

        <div>
          <label htmlFor="longitude" className="block text-sm font-medium mb-1">
            Longitude
          </label>
          <input
            type="text"
            id="longitude"
            value={longitude}
            onChange={(e) => setLongitude(parseFloat(e.target.value))}
            className={`w-full px-3 py-2 border rounded-md ${!isValid ? 'border-red-500' : 'border-gray-300'}`}
            placeholder="e.g. 1.4442"
          />
        </div>

        <div>
          <label htmlFor="baroalt" className="block text-sm font-medium mb-1">
            Barometer Altitude
          </label>
          <input
            type="text"
            id="baroalt"
            value={baroalt}
            onChange={(e) => setBaroalt(parseFloat(e.target.value))}
            className={`w-full px-3 py-2 border rounded-md ${!isValid ? 'border-red-500' : 'border-gray-300'}`}
            placeholder="e.g. 1.4442"
          />
        </div>

        {!isValid && (
          <p className="text-red-500 text-sm">Please enter valid GPS coordinates</p>
        )}

        <button
          type="submit"
          className="w-full bg-sidebar-primary text-sidebar-primary-foreground py-2 px-4 rounded-md hover:bg-opacity-90 transition-colors"
        >
          Update Position
        </button>
      </form>

      <div className="mt-8">
        <h2 className="text-lg font-semibold mb-2">Modes</h2>
        <div className="space-y-2">
          <button
            className={`w-full py-2 px-4 rounded-md transition-colors ${observerPosition ? 'bg-sidebar-primary hover:bg-opacity-90' : 'bg-gray-400 cursor-not-allowed'}`}
            onClick={() => handleModeSelect('airplane')}
            disabled={!observerPosition}
          >
            Observer to Airplane
          </button>
          <button
            className={`w-full py-2 px-4 rounded-md transition-colors ${observerPosition ? 'bg-sidebar-primary hover:bg-opacity-90' : 'bg-gray-400 cursor-not-allowed'}`}
            onClick={() => handleModeSelect('satellite')}
            disabled={!observerPosition}
          >
            Observer to Satellite
          </button>
          <button
            className={`w-full py-2 px-4 rounded-md transition-colors ${observerPosition ? 'bg-sidebar-primary hover:bg-opacity-90' : 'bg-gray-400 cursor-not-allowed'}`}
            onClick={() => handleModeSelect('spatial')}
            disabled={!observerPosition}
          >
            Observer to Spatial Body
          </button>
        </div>
      </div>

      <FlightSidebar />
    </div>
  )
}