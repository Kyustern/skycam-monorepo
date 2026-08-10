import * as THREE from 'three';
import { gpsToScenePosition } from './cameraUtils';
import { SCENE_EARTH_RADIUS } from './unitConversions';

// Type for objects that can be used to compute angles
// Must have latitude, longitude, and baro_altitude properties
export interface PositionObject {
  latitude: number;
  longitude: number;
  baro_altitude: number;
}

// NORTH_POLE constant used for reference
const NORTH_POLE = new THREE.Vector3(0, SCENE_EARTH_RADIUS, 0);

/**
 * Compute azimuth and vertical angle between two positions
 * 
 * @param observer - The observer position (must have latitude, longitude, baro_altitude)
 * @param target - The target position (must have latitude, longitude, baro_altitude)
 * @returns Object containing signedAzimuth (in radians) and verticalAngle (in radians)
 * 
 * The azimuth is the horizontal angle from north, positive clockwise.
 * The vertical angle is the angle above or below the horizontal plane.
 */
export function computeAngles(observer: PositionObject, target: PositionObject): {
  signedAzimuth: number;
  verticalAngle: number;
} {
  // Convert both positions to 3D scene coordinates
  const observerPoint = gpsToScenePosition(
    observer.latitude,
    observer.longitude,
    observer.baro_altitude
  );
  const targetPoint = gpsToScenePosition(
    target.latitude,
    target.longitude,
    target.baro_altitude
  );

  // Calculate reference vectors
  const up = observerPoint.clone().normalize();
  const north = NORTH_POLE.clone().sub(up.clone().multiplyScalar(NORTH_POLE.dot(up))).normalize();
  const east = new THREE.Vector3().crossVectors(north, up).normalize();
  const toTarget = targetPoint.clone().sub(observerPoint);

  // Calculate horizontal direction to target (projected onto horizontal plane)
  const horizontalTargetDirection = toTarget.clone()
    .sub(up.clone().multiplyScalar(toTarget.dot(up)))
    .normalize();

  // Calculate azimuth: angle from north to target in horizontal plane
  // atan2(east_component, north_component) gives angle from north, positive eastward
  const azimuth = Math.atan2(
    horizontalTargetDirection.dot(east),
    horizontalTargetDirection.dot(north)
  );

  // Calculate vertical angle: angle above or below horizontal plane
  const vertical = Math.asin(toTarget.clone().normalize().dot(up));

  return {
    signedAzimuth: azimuth,
    verticalAngle: vertical,
  };
}

/**
 * Compute azimuth and vertical angle and convert to degrees
 * 
 * @param observer - The observer position (must have latitude, longitude, baro_altitude)
 * @param target - The target position (must have latitude, longitude, baro_altitude)
 * @returns Object containing signedAzimuth (in degrees) and verticalAngle (in degrees)
 */
export function computeAnglesDegrees(observer: PositionObject, target: PositionObject): {
  signedAzimuth: number;
  verticalAngle: number;
} {
  const { signedAzimuth, verticalAngle } = computeAngles(observer, target);
  
  return {
    signedAzimuth: THREE.MathUtils.radToDeg(signedAzimuth),
    verticalAngle: THREE.MathUtils.radToDeg(verticalAngle),
  };
}

/**
 * Format angle as a string with degree symbol
 * 
 * @param radians - Angle in radians
 * @returns Formatted string like "+45.0°" or "-30.5°"
 */
export function formatAngle(radians: number): string {
  const degrees = THREE.MathUtils.radToDeg(radians);
  return `${degrees > 0 ? '+' : ''}${degrees.toFixed(1)}°`;
}

/**
 * Format angle from degrees as a string with degree symbol
 * 
 * @param degrees - Angle in degrees
 * @returns Formatted string like "+45.0°" or "-30.5°"
 */
export function formatAngleDegrees(degrees: number): string {
  return `${degrees > 0 ? '+' : ''}${degrees.toFixed(1)}°`;
}
