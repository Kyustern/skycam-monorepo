import { useMemo } from 'react'
import * as THREE from 'three'
import { useStore } from '../store/useStore'
import { gpsToScenePosition } from '../utilities/cameraUtils'
import { kmToSceneUnits, SCENE_EARTH_RADIUS } from '../utilities/unitConversions'

const NORTH_POLE = new THREE.Vector3(0, SCENE_EARTH_RADIUS, 0)
const SEGMENTS = 48

export const AzimuthAngleOverlay = () => {
  const observerPosition = useStore(state => state.observerPosition)
  const selectedFlight = useStore(state => state.selectedFlight)
  // const flightsHash = useStore(state => state.flightsHash)
  const flights = useStore(state => state.flights)
  
  const overlay = useMemo(() => {
    // console.log('LTES - flightsHash', flightsHash);
    if (!observerPosition || !selectedFlight) return null
    const currentSelectedFlight = flights[selectedFlight.callsign.trim().toLocaleUpperCase()]
    if (!currentSelectedFlight) return null

    const observerPoint = gpsToScenePosition(
      observerPosition.latitude,
      observerPosition.longitude,
      observerPosition.baro_altitude
    )
    const flightPoint = gpsToScenePosition(
      currentSelectedFlight.latitude,
      currentSelectedFlight.longitude,
      currentSelectedFlight.baro_altitude
    )

    const up = observerPoint.clone().normalize()
    const north = NORTH_POLE.clone().sub(up.clone().multiplyScalar(NORTH_POLE.dot(up))).normalize()
    const east = new THREE.Vector3().crossVectors(north, up).normalize()
    const toFlight = flightPoint.clone().sub(observerPoint)

    const horizontalFlightDirection = toFlight.clone().sub(up.clone().multiplyScalar(toFlight.dot(up))).normalize()

    const signedAzimuth = Math.atan2(
      horizontalFlightDirection.dot(east),
      horizontalFlightDirection.dot(north)
    )
    const verticalAngle = Math.asin(toFlight.clone().normalize().dot(up))
    const radius = toFlight.length()
    const center = up.clone().multiplyScalar(observerPoint.length())

    const vertices: number[] = []
    for (let index = 0; index < SEGMENTS; index += 1) {
      const startAngle = (signedAzimuth * index) / SEGMENTS
      const endAngle = (signedAzimuth * (index + 1)) / SEGMENTS
      const startPoint = center.clone().add(
        north.clone().multiplyScalar(Math.cos(startAngle) * radius)
          .add(east.clone().multiplyScalar(Math.sin(startAngle) * radius))
      )
      const endPoint = center.clone().add(
        north.clone().multiplyScalar(Math.cos(endAngle) * radius)
          .add(east.clone().multiplyScalar(Math.sin(endAngle) * radius))
      )

      vertices.push(center.x, center.y, center.z)
      vertices.push(startPoint.x, startPoint.y, startPoint.z)
      vertices.push(endPoint.x, endPoint.y, endPoint.z)
    }

    const sectorGeometry = new THREE.BufferGeometry()
    sectorGeometry.setAttribute('position', new THREE.Float32BufferAttribute(vertices, 3))
    sectorGeometry.computeVertexNormals()

    const northRayGeometry = new THREE.BufferGeometry().setFromPoints([
      center,
      center.clone().add(north.clone().multiplyScalar(radius)),
    ])
    const flightRayGeometry = new THREE.BufferGeometry().setFromPoints([
      center,
      center.clone().add(horizontalFlightDirection.clone().multiplyScalar(radius)),
    ])

    // Vertical sector - shows elevation angle
    const verticalVertices: number[] = []
    const verticalSegments = 16
    const verticalRadius = radius * 1
    const verticalPlaneNormal = new THREE.Vector3().crossVectors(horizontalFlightDirection, up).normalize()
    const verticalPlaneRight = new THREE.Vector3().crossVectors(up, verticalPlaneNormal).normalize()

    for (let i = 0; i <= verticalSegments; i++) {
      const t = i / verticalSegments
      const angle = verticalAngle * t
      const cosA = Math.cos(angle)
      const sinA = Math.sin(angle)

      verticalVertices.push(center.x, center.y, center.z)
      verticalVertices.push(
        center.x + verticalPlaneRight.x * cosA * verticalRadius,
        center.y + verticalPlaneRight.y * cosA * verticalRadius + up.y * sinA * verticalRadius,
        center.z + verticalPlaneRight.z * cosA * verticalRadius + up.z * sinA * verticalRadius
      )
      if (i > 0) {
        const prevCosA = Math.cos(verticalAngle * (i - 1) / verticalSegments)
        const prevSinA = Math.sin(verticalAngle * (i - 1) / verticalSegments)
        verticalVertices.push(
          center.x + verticalPlaneRight.x * prevCosA * verticalRadius,
          center.y + verticalPlaneRight.y * prevCosA * verticalRadius + up.y * prevSinA * verticalRadius,
          center.z + verticalPlaneRight.z * prevCosA * verticalRadius + up.z * prevSinA * verticalRadius
        )
      }
    }

    const verticalSectorGeometry = new THREE.BufferGeometry()
    verticalSectorGeometry.setAttribute('position', new THREE.Float32BufferAttribute(verticalVertices, 3))

    // Actual 3D flight direction line
    const actualFlightRayGeometry = new THREE.BufferGeometry().setFromPoints([
      center,
      center.clone().add(toFlight.clone().normalize().multiplyScalar(radius)),
    ])

    return {
      sectorGeometry,
      northRayGeometry,
      flightRayGeometry,
      verticalSectorGeometry,
      actualFlightRayGeometry,
    }
  }, [observerPosition, selectedFlight, flights])

  if (!overlay) return null

  return (
    <group>
      <mesh geometry={overlay.sectorGeometry}>
        <meshBasicMaterial color="#facc15" transparent opacity={0.22} side={THREE.DoubleSide} />
      </mesh>
      <mesh geometry={overlay.verticalSectorGeometry}>
        <meshBasicMaterial color="#38bdf8" transparent opacity={0.3} side={THREE.DoubleSide} />
      </mesh>
    </group>
  )
}
