import { useMemo } from 'react'
import * as THREE from 'three'
import { useStore } from '../../store/useStore'
import { gpsToScenePosition } from '../../utilities/cameraUtils'
import { SCENE_EARTH_RADIUS } from '../../utilities/unitConversions'

const NORTH_POLE = new THREE.Vector3(0, SCENE_EARTH_RADIUS, 0)

const formatAngle = (radians: number) => {
  const degrees = THREE.MathUtils.radToDeg(radians)
  return `${degrees > 0 ? '+' : ''}${degrees.toFixed(1)}°`
}

export const AngleDisplay = () => {
  const observerPosition = useStore(state => state.observerPosition)
  const selectedFlight = useStore(state => state.selectedFlight)

  const { signedAzimuth, verticalAngle } = useMemo(() => {
    if (!observerPosition || !selectedFlight) {
      return { signedAzimuth: 0, verticalAngle: 0 }
    }

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

    const up = observerPoint.clone().normalize()
    const north = NORTH_POLE.clone().sub(up.clone().multiplyScalar(NORTH_POLE.dot(up))).normalize()
    const east = new THREE.Vector3().crossVectors(north, up).normalize()
    const toFlight = flightPoint.clone().sub(observerPoint)

    const horizontalFlightDirection = toFlight.clone().sub(up.clone().multiplyScalar(toFlight.dot(up))).normalize()

    const azimuth = Math.atan2(
      horizontalFlightDirection.dot(east),
      horizontalFlightDirection.dot(north)
    )
    const vertical = Math.asin(toFlight.clone().normalize().dot(up))

    return { signedAzimuth: azimuth, verticalAngle: vertical }
  }, [observerPosition, selectedFlight])

  if (!observerPosition || !selectedFlight) return null

  return (
    <div className="bg-black/70 text-white p-2 rounded text-xs font-mono">
      <div>
        <span style={{ color: '#facc15' }}>Azimuth: </span>
        <span style={{ color: '#facc15' }}>{formatAngle(signedAzimuth)}</span>
      </div>
      <div>
        <span style={{ color: '#38bdf8' }}>Vertical: </span>
        <span style={{ color: '#38bdf8' }}>{formatAngle(verticalAngle)}</span>
      </div>
    </div>
  )
}
