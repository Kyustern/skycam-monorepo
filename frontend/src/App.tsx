import { Sidebar } from './components/layout/Sidebar'
import { MainScene } from './components/layout/MainScene'
import { useEffect, useRef } from 'react'
import { useStore } from '@/store/useStore'
    import { AircraftDataProvider, useAircraftData } from './contexts'
import type { OrbitControls as OrbitControlsImpl } from 'three-stdlib'

function App() {
  const setFlights = useStore(state => state.setFlights)
  const observerPosition = useStore(state => state.observerPosition)
  const controlsRef = useRef<OrbitControlsImpl>(null)
  const { error: aircraftDataError, formattedAircraftData, isLoading: aircraftDataLoading, refresh } = useAircraftData()

  // Update flights in store when data is loaded
  useEffect(() => {
    if (!aircraftDataLoading && !aircraftDataError && setFlights && formattedAircraftData) {
      setFlights(formattedAircraftData)
    }
  }, [aircraftDataLoading, formattedAircraftData, aircraftDataError, setFlights])

  // Refresh aircraft data when observer position changes
  useEffect(() => {
    if (observerPosition) {
      refresh(observerPosition)
    }
  }, [observerPosition, refresh])

  return (
    <div className="grid grid-cols-[20rem_auto] h-screen">
      <Sidebar controlsRef={controlsRef} />
      <MainScene controlsRef={controlsRef} />
    </div>
  )
}

export default App