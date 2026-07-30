/**
 * Unit conversion utilities for the 3D scene
 * Earth radius in scene: 5 units
 * Real Earth radius: ~6,371 km
 */

// Real Earth radius in kilometers
export const REAL_EARTH_RADIUS_KM = 6371

// Scene Earth radius in units
export const SCENE_EARTH_RADIUS = 5

const scaleFactor = SCENE_EARTH_RADIUS / REAL_EARTH_RADIUS_KM
/**
 * Convert kilometers to scene units
 * @param km - Distance in kilometers
 * @returns Distance in scene units
 */
export function kmToSceneUnits(km: number): number {
  return km * scaleFactor
}

/**
 * Convert scene units to kilometers
 * @param units - Distance in scene units
 * @returns Distance in kilometers
 */
export function sceneUnitsToKm(units: number): number {
  const scaleFactor = REAL_EARTH_RADIUS_KM / SCENE_EARTH_RADIUS
  return units * scaleFactor
}

/**
 * Convert meters to scene units
 * @param meters - Distance in meters
 * @returns Distance in scene units
 */
export function metersToSceneUnits(meters: number): number {
  return kmToSceneUnits(meters / 1000)
}

/**
 * Convert scene units to meters
 * @param units - Distance in scene units
 * @returns Distance in meters
 */
export function sceneUnitsToMeters(units: number): number {
  return sceneUnitsToKm(units) * 1000
}

/**
 * Get the scale factor for converting real-world distances to scene units
 * @returns The scale factor (scene units per kilometer)
 */
export function getSceneScaleFactor(): number {
  return SCENE_EARTH_RADIUS / REAL_EARTH_RADIUS_KM
}

/**
 * Calculate the appropriate size for an object in the scene based on its real-world size
 * @param realSizeKm - The real-world size in kilometers
 * @param scale - Optional scale factor (default: 1)
 * @returns The size in scene units
 */
export function calculateSceneSize(realSizeKm: number, scale: number = 1): number {
  return kmToSceneUnits(realSizeKm) * scale
}