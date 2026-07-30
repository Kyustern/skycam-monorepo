import { useMemo } from 'react'
import * as THREE from 'three'
import '@react-three/fiber'
import { useStore } from '../store/useStore'
import { kmToSceneUnits } from '../utilities/unitConversions'
import { gpsToScenePosition } from '@/utilities/cameraUtils'

export const ObserverMarker = () => {
  const selectedFlight = useStore(state => state.selectedFlight)
  const observerPosition = useStore(state => state.observerPosition)
  const observerFlightDistance = useMemo(() => {
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

      const trajToFlightVec  = observerPoint.sub(flightPoint)

      trajToFlightVec.z = 0

       return trajToFlightVec.length()

    }
  }, [observerPosition, selectedFlight])

  const { position, quaternion } = useMemo(() => {
    if (!observerPosition) return { position: null, quaternion: null }

    const radius = 5
    const latRad = THREE.MathUtils.degToRad(observerPosition.latitude)
    const lonRad = THREE.MathUtils.degToRad(observerPosition.longitude)

    const x = radius * Math.cos(latRad) * Math.sin(lonRad)
    const y = radius * Math.sin(latRad)
    const z = radius * Math.cos(latRad) * Math.cos(lonRad)

    const pos = new THREE.Vector3(x, y, z)
    const q = new THREE.Quaternion().setFromUnitVectors(
      new THREE.Vector3(0, 0, 1),
      pos.clone().negate().normalize()
    )

    return { position: pos, quaternion: q }
  }, [observerPosition])

  if (!position) return null

  return (
    <>
      <mesh position={position}>
        <sphereGeometry args={[kmToSceneUnits(1), 16, 16]} />
        <meshBasicMaterial color="blue" transparent opacity={1} />
      </mesh>
      <mesh position={position} quaternion={quaternion}>
        <circleGeometry args={[kmToSceneUnits(100), 32, 0, Math.PI * 2]} />
        <meshBasicMaterial color="green" transparent opacity={0.5} side={THREE.DoubleSide} />
      </mesh>
    </>
  )
}
