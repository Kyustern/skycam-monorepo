import { useCallback, useMemo } from 'react'
import * as THREE from 'three'
import { useStore } from '../store/useStore'
import { kmToSceneUnits, metersToSceneUnits } from '../utilities/unitConversions'
import { FlightState } from '@/scripts/scrap-airplane'

export const PredictionMarker = () => {
  const selectedFlight = useStore(state => state.selectedFlight)
  const setSelectedFlight = useStore(state => state.setSelectedFlight)
  const predictions = useStore(state => state.predictions)

  const computeFlightPosVector = useCallback((flight: FlightState) => {
    // Convert GPS coordinates to 3D position on sphere with altitude
    const earthRadius = 5
    const altitudeScale = 1 // Scale factor for altitude visualization

    const latRad = THREE.MathUtils.degToRad(flight.latitude)
    const lonRad = THREE.MathUtils.degToRad(flight.longitude)

    // Calculate position on earth surface
    const surfaceX = earthRadius * Math.cos(latRad) * Math.sin(lonRad)
    const surfaceY = earthRadius * Math.sin(latRad)
    const surfaceZ = earthRadius * Math.cos(latRad) * Math.cos(lonRad)

    // Add altitude (scaled for visualization)
    const altitudeOffset = metersToSceneUnits(flight.baro_altitude * altitudeScale)
    const x = surfaceX + altitudeOffset * Math.cos(latRad) * Math.sin(lonRad)
    const y = surfaceY + altitudeOffset * Math.sin(latRad)
    const z = surfaceZ + altitudeOffset * Math.cos(latRad) * Math.cos(lonRad)

    const flightPos = new THREE.Vector3(x, y, z)

    return {
      flightPos
    }
  })

  const markers = useMemo(() => {
    if (!predictions) return null;
    return Object.values(predictions).map((flight) => {
      const { flightPos } = computeFlightPosVector(flight);
      const isSelectedFlight = flight.callsign === selectedFlight?.callsign;

      return (
        <group position={flightPos} key={`pred-${flight.callsign}`} renderOrder={isSelectedFlight ? 1 : 0}>
          {/* Sphere marker for prediction - no label */}
          <mesh 
            renderOrder={isSelectedFlight ? 2 : 0} 
            onClick={(e) => { 
              e.stopPropagation(); 
              setSelectedFlight(flight); 
            }}
          >
            <sphereGeometry args={[kmToSceneUnits(1), 32, 32]} />
            <meshStandardMaterial
              color={isSelectedFlight ? "#ffff00" : "#808080"}
              depthTest={!isSelectedFlight}
              depthWrite={!isSelectedFlight}
            />
          </mesh>
        </group>
      );
    });
  }, [computeFlightPosVector, predictions, selectedFlight?.callsign, setSelectedFlight]);
  
  if (!predictions) return null

  return <>{markers}</>
}
