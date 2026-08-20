import { Sidebar } from './components/layout/Sidebar'
import { MainScene } from './components/layout/MainScene'
import { useEffect, useRef } from 'react'
import { useStore } from '@/store/useStore'
import { useWebSocketStore } from '@/store/useWebSocketStore'
import type { OrbitControls as OrbitControlsImpl } from 'three-stdlib'

function App() {
  const setFlights = useStore(state => state.setFlights)
  const observerPosition = useStore(state => state.observerPosition)
  const searchRadius = useStore(state => state.searchRadius)
  const controlsRef = useRef<OrbitControlsImpl>(null)
  
  const { 
    flights: wsFlights, 
    error: wsError, 
    isLoading: wsLoading, 
    fetchAndUpdateData,
    reconnect,
    socketReadyState 
  } = useWebSocketStore();

  // Initialize websocket connection on mount
  useEffect(() => {
    reconnect();
    
    return () => {
      // Cleanup will be handled by the store's disconnect
    };
  }, [reconnect]);

  // Update flights in store when websocket data is loaded
  useEffect(() => {
    if (!wsLoading && !wsError && setFlights && wsFlights) {
      setFlights(wsFlights)
    }
  }, [wsLoading, wsFlights, wsError, setFlights])

  // Refresh aircraft data when observer position changes
  useEffect(() => {
    if (observerPosition) {
      fetchAndUpdateData({observer_position: observerPosition, radius: searchRadius})
    }
  }, [observerPosition, searchRadius, fetchAndUpdateData])

  return (
    <div className="grid grid-cols-[20rem_auto] h-screen">
      <Sidebar controlsRef={controlsRef} />
      <MainScene controlsRef={controlsRef} />
    </div>
  )
}

export default App
