import { useMemo } from 'react'
import * as THREE from 'three'
import { useStore } from '../store/useStore'
import { gpsToScenePosition } from '../utilities/cameraUtils'

export const ConnectionLine = () => {
  const observerPosition = useStore(state => state.observerPosition)
  const selectedFlight = useStore(state => state.selectedFlight)
  const flightsHash = useStore(state => state.flightsHash)
  const flights = useStore(state => state.flights)

  const line = useMemo(() => {
    if (observerPosition && selectedFlight && flights && selectedFlight != null) {
      const observerPoint = gpsToScenePosition(
        observerPosition.latitude,
        observerPosition.longitude,
        observerPosition.baro_altitude
      )
      const currentSelectedFlight = flights[selectedFlight.callsign.trim()]
      if (!currentSelectedFlight) return null
      const flightPoint = gpsToScenePosition(
        currentSelectedFlight.latitude,
        currentSelectedFlight.longitude,
        currentSelectedFlight.baro_altitude
      )
      
      // Create line geometry
      const points = [observerPoint, flightPoint]

      
      const geometry = new THREE.BufferGeometry().setFromPoints(points)
      const material = new THREE.LineBasicMaterial({ color: 0xffff00, linewidth: 2 })
      const newLine = new THREE.Line(geometry, material)
      
      return newLine
    }  
    //@ts-expect-error Necessary for the line to follow the updating position
  }, [observerPosition, selectedFlight, flights, flightsHash])

  if (!line) return null

  return <primitive object={line} />
}
