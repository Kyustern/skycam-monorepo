import * as THREE from 'three'
import { metersToSceneUnits, SCENE_EARTH_RADIUS } from './unitConversions'

type FocusControls = {
  target: THREE.Vector3
  update: () => void
} | null

/**
 * Convert GPS coordinates to 3D position on a sphere
 * @param lat - Latitude in degrees
 * @param lon - Longitude in degrees
 * @param radius - Radius of the sphere (default: 5)
 * @param altitude - Altitude above surface in same units as radius (default: 0)
 * @returns THREE.Vector3 with the 3D position
 */
export function gpsToScenePosition(
  lat: number,
  lon: number,
  altitude_meters: number = 0
): THREE.Vector3 {
  const latRad = THREE.MathUtils.degToRad(lat)
  const lonRad = THREE.MathUtils.degToRad(lon)
  
  const totalRadius = SCENE_EARTH_RADIUS + metersToSceneUnits(altitude_meters)
  
  const x = totalRadius * Math.cos(latRad) * Math.sin(lonRad)
  const y = totalRadius * Math.sin(latRad)
  const z = totalRadius * Math.cos(latRad) * Math.cos(lonRad)
  
  return new THREE.Vector3(x, y, z)
}

/**
 * Set camera focus to a specific GPS coordinate
 * @param controls - OrbitControls instance
 * @param lat - Latitude in degrees
 * @param lon - Longitude in degrees
 * @param alt - Radius of the target sphere (default: 5)
 * @returns The converted gps coordinates to scene coordinates
 */
export function focusCameraOnGPS(
  controls: FocusControls,
  lat: number,
  lon: number,
  alt: number = 5
) {
  // console.log("radius", alt);
  // console.log("lon", lon);
  // console.log("lat", lat);
  const targetPosition = gpsToScenePosition(lat, lon, alt)
  if (controls) {
    controls.target.copy(targetPosition)
    controls.update()
  }
  return targetPosition
}

/**
 * Set camera focus to a specific 3D position
 * @param controls - OrbitControls instance
 * @param position - Target position as THREE.Vector3
 */
export function focusCameraOnPosition(
  controls: FocusControls,
  position: THREE.Vector3
): void {
  if (controls) {
    controls.target.copy(position)
    controls.update()
  }
}

/**
 * Animate camera to focus on a new position smoothly
 * @param controls - OrbitControls instance
 * @param targetPosition - Target position to focus on
 * @param duration - Animation duration in milliseconds (default: 1000)
 */
export function animateCameraFocus(
  controls: FocusControls,
  targetPosition: THREE.Vector3,
  duration: number = 1000
): void {
  if (!controls) return
  
  const startPosition = controls.target.clone()
  const startTime = performance.now()
  
  function animate() {
    const elapsed = performance.now() - startTime
    const progress = Math.min(elapsed / duration, 1)
    
    // Ease in out animation
    const easedProgress = progress < 0.5 
      ? 2 * progress * progress
      : -1 + (4 - 2 * progress) * progress
    
    controls.target.lerpVectors(startPosition, targetPosition, easedProgress)
    controls.update()
    
    if (progress < 1) {
      requestAnimationFrame(animate)
    }
  }
  
  requestAnimationFrame(animate)
}

/**
 * Get current camera focus position
 * @param controls - OrbitControls instance
 * @returns Current target position as THREE.Vector3
 */
export function getCurrentCameraFocus(controls: FocusControls): THREE.Vector3 {
  return controls ? controls.target.clone() : new THREE.Vector3()
}
