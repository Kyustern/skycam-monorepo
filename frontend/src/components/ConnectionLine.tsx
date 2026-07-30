import { useMemo } from 'react'
import * as THREE from 'three'
import { useStore } from '../store/useStore'
import { gpsToScenePosition } from '../utilities/cameraUtils'

export const ConnectionLine = () => {
  const observerPosition = useStore(state => state.observerPosition)
  const selectedFlight = useStore(state => state.selectedFlight)

  const line = useMemo(() => {
    if (observerPosition && selectedFlight) {
      const observerPoint = gpsToScenePosition(
        observerPosition.latitude,
        observerPosition.longitude,
        observerPosition.baro_altitude
      )
      const flightPoint = gpsToScenePosition(
        selectedFlight.latitude,
        selectedFlight.longitude,
        selectedFlight.baro_altitude
      )
      
      // Create line geometry
      const points = [observerPoint, flightPoint]
      
      const geometry = new THREE.BufferGeometry().setFromPoints(points)
      const material = new THREE.LineBasicMaterial({ color: 0xffff00, linewidth: 2 })
      const newLine = new THREE.Line(geometry, material)
      
      return newLine
    }  
  }, [observerPosition, selectedFlight])

  if (!line) return null

  return <primitive object={line} />
}
