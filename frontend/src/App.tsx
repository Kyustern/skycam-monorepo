import { Sidebar } from './components/layout/Sidebar'
import { MainScene } from './components/layout/MainScene'
import { useEffect } from 'react'
import { useStore } from '@/store/useStore'
import { Flights } from './scripts/scrap-airplane'
import { useAircraftData } from './hooks/useAircraftData'

function App() {
  const setFlights = useStore(state => state.setFlights)
  const observerPosition = useStore(state => state.observerPosition)

  const {error: aircraftDataError, formattedAircraftData, isLoading: aircraftDataLoading, refresh} = useAircraftData({ observerPosition })
  // Fetch flight data from assets

  useEffect(() => {
    if (!aircraftDataLoading && !aircraftDataError && setFlights) {
      setFlights(formattedAircraftData)
    }
  }, [aircraftDataLoading, formattedAircraftData, aircraftDataError, setFlights])

  useEffect(() => {
    refresh(observerPosition)
  }, [observerPosition, refresh])

  return (
    <div className="grid grid-cols-[10%_90%]">
      <Sidebar />
      <MainScene />
    </div>
  )
}

export default App