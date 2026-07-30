import * as THREE from 'three'

/**
 * Calculate the viewport dimensions in scene units at a specific distance from camera
 * @param camera - Three.js camera
 * @param distance - Distance from camera to target plane
 * @returns Object with width and height in scene units
 */
export function getViewportSizeInUnits(camera: THREE.Camera, distance: number): { width: number, height: number } {
  if (!(camera instanceof THREE.PerspectiveCamera)) {
    console.warn('Viewport size calculation works best with PerspectiveCamera')
    return { width: 0, height: 0 }
  }

  // Calculate viewport dimensions based on camera FOV and distance
  const vFOV = THREE.MathUtils.degToRad(camera.fov)
  const height = 2 * Math.tan(vFOV / 2) * distance
  const width = height * camera.aspect

  return { width, height }
}

/**
 * Calculate the size of 1 unit at a specific distance from camera (in pixels)
 * @param camera - Three.js camera
 * @param distance - Distance from camera to object
 * @param renderer - Three.js renderer
 * @returns Size in pixels
 */
export function getUnitSizeInPixels(camera: THREE.Camera, distance: number, renderer: THREE.Renderer): number {
  const viewportSize = getViewportSizeInUnits(camera, distance)
  const pixelSize = renderer.getSize(new THREE.Vector2())
  
  return pixelSize.width / viewportSize.width
}

/**
 * Get the distance from camera to a specific point in the scene
 * @param camera - Three.js camera
 * @param point - Target point in 3D space
 * @returns Distance from camera to point
 */
export function getCameraDistanceToPoint(camera: THREE.Camera, point: THREE.Vector3): number {
  return camera.position.distanceTo(point)
}

/**
 * Calculate the appropriate size for an object to appear consistent at different distances
 * @param camera - Three.js camera
 * @param point - Position of the object
 * @param desiredPixelSize - Desired size in pixels
 * @param renderer - Three.js renderer
 * @returns Size in scene units
 */
export function calculateSizeForConsistentAppearance(
  camera: THREE.Camera,
  point: THREE.Vector3,
  desiredPixelSize: number,
  renderer: THREE.Renderer
): number {
  const distance = getCameraDistanceToPoint(camera, point)
  const pixelsPerUnit = getUnitSizeInPixels(camera, distance, renderer)
  
  return desiredPixelSize / pixelsPerUnit
}