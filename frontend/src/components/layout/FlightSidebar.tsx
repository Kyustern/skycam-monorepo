import { useStore } from '../../store/useStore'
import type { FlightState } from '../../scripts/scrap-airplane'

export const FlightSidebar = () => {
  const selectionMode = useStore(state => state.selectionMode)
  const setSelectionMode = useStore(state => state.setSelectionMode)
  const setSelectedFlight = useStore(state => state.setSelectedFlight)
  const flights = useStore(state => state.flights)
  // const [flights, setFlights] = useState<FormattedAircraftData | null>()


  const handleFlightSelect = (flight: FlightState) => {
    setSelectedFlight(flight)
    setSelectionMode(null)
  }

  if (selectionMode !== 'airplane') return null

  if (!flights) return (
        <div className="flex items-center justify-center h-[70vh]">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-sidebar-primary"></div>
          <span className="ml-2">Loading flights...</span>
        </div>
      )

      if (flights) return (
    <div className="fixed left-[10%] top-0 h-full w-64 sidebar text-sidebar-foreground p-4 z-20 shadow-lg dark-theme">
      <h2 className="text-lg font-semibold mb-4">Select Flight</h2>
      
        <div className="space-y-2 overflow-y-auto h-[70vh] sidebar-accent rounded-lg p-2">
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
      
      {/* Close button */}
      <button
        onClick={() => setSelectionMode(null)}
        className="absolute top-4 right-4 accent text-sidebar-primary-foreground px-2 py-1 rounded hover:bg-opacity-80 transition-colors"
      >
        ×
      </button>
    </div>
  )
}
