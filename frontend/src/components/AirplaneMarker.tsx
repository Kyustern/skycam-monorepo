import { useCallback, useMemo } from 'react'
import * as THREE from 'three'
import { Html } from '@react-three/drei'
import { useStore } from '../store/useStore'
import { kmToSceneUnits, metersToSceneUnits, REAL_EARTH_RADIUS_KM } from '../utilities/unitConversions'
import { FlightState } from '@/scripts/scrap-airplane'
import { LineGeometry } from 'three/examples/jsm/Addons.js'
import { animateCameraFocus } from '@/utilities/cameraUtils'

export const AirplaneMarker = () => {
  // const [position, setPosition] = useState<THREE.Vector3>(new THREE.Vector3())
  const selectedFlight = useStore(state => state.selectedFlight)
  const flights = useStore(state => state.flights)
  const controls = useStore(state => state.controls)

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
    // const altitudeOffset = selectedFlight.baro_altitude * altitudeScale
    const altitudeOffset = metersToSceneUnits(flight.baro_altitude * altitudeScale)
    const x = surfaceX + altitudeOffset * Math.cos(latRad) * Math.sin(lonRad)
    const y = surfaceY + altitudeOffset * Math.sin(latRad)
    const z = surfaceZ + altitudeOffset * Math.cos(latRad) * Math.cos(lonRad)

    const flightPos = new THREE.Vector3(x, y, z)
    const q = new THREE.Quaternion().setFromUnitVectors(
      new THREE.Vector3(0, 0, 1),
      flightPos.clone().negate().normalize()
    )

    const textPos = flightPos.clone().normalize().multiplyScalar(metersToSceneUnits(10000))
    // const textPos = flightPos.clone().add(
    //   flightPos.clone().normalize().multiplyScalar(textOffset)
    // )

    if (flight.callsign === selectedFlight?.callsign && controls) {
      animateCameraFocus(
        controls,
        textPos
      )
    }

    const geometry = new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(0, 0, 0), textPos])
    const material = new THREE.LineBasicMaterial({ color: 0xffff00, linewidth: 2 })
    const connectionLine = new THREE.Line(geometry, material)
    return {
      flightPos,
      textPos,
      connectionLine,
      q
    }
  })

  const markers = useMemo(() => {
    if (!flights) return null;
    return Object.values(flights).map((flight) => {
      const { flightPos, q, textPos, connectionLine
      } = computeFlightPosVector(flight);
      const isSelectedFlight = flight.callsign === selectedFlight?.callsign;

      return (
        <group position={flightPos} renderOrder={isSelectedFlight ? 1 : 0}>
          {/* Sphere with depth testing disabled */}
          <mesh renderOrder={isSelectedFlight ? 2 : 0}>
            <sphereGeometry args={[kmToSceneUnits(1), 32, 32]} />
            <meshStandardMaterial
              color={isSelectedFlight ? "#38bdf8" : "green"}
              depthTest={!isSelectedFlight}
              depthWrite={!isSelectedFlight}
            />
          </mesh>

          <primitive object={connectionLine} />

          {/* <line>
            <bufferGeometry attach="geometry" {...connectionGeometry} />
            <lineBasicMaterial color={isSelectedFlight ? "#38bdf8" : "grey"} linecap='butt' linewidth={2} />
          </line> */}

          {/* HTML label */}
          <Html
            position={textPos}
            quaternion={q}
            distanceFactor={0.1}
            style={{
              color: isSelectedFlight ? "#38bdf8" : "white",
              fontSize: '14px',
              fontFamily: 'sans-serif',
              background: 'rgba(0,0,0,0.5)',
              padding: '4px 8px',
              borderRadius: '4px',
              margin: 0,
              transform: 'translate(-50%, -50%)',
              zIndex: isSelectedFlight ? 100 : "inherit",
              pointerEvents: 'none', // Prevents HTML from blocking interactions
            }}
          >
            {flight.callsign}
          </Html>
        </group>
      );
    });
  }, [computeFlightPosVector, flights, selectedFlight?.callsign]);
  if (!selectedFlight) return null

  return (markers)
}
