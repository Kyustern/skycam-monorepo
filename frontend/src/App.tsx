import { Sidebar } from './components/layout/Sidebar'
import { MainScene } from './components/layout/MainScene'
import { useEffect, useRef } from 'react'
import { useStore } from '@/store/useStore'
import type { OrbitControls as OrbitControlsImpl } from 'three-stdlib'

function App() {
  const observerPosition = useStore(state => state.observerPosition)
  const searchRadius = useStore(state => state.searchRadius)
  const controlsRef = useRef<OrbitControlsImpl>(null)
  
  const { 
    fetchAndUpdateData,
    reconnect
  } = useStore();

  // Initialize websocket connection on mount
  useEffect(() => {
    reconnect();
    
    return () => {
      // Cleanup will be handled by the store's disconnect
    };
  }, []); // Empty dependency array - reconnect is stable from Zustand

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
