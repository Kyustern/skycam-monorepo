// Conversion utility functions

//      DISTANCE

/**
 * Convert feet to kilometers
 * @param feet - Value in feet
 * @returns Value in kilometers
 */
export function feetToKm(feet: number): number {
    return feet * 0.0003048;
}

/**
 * Convert miles to kilometers
 * @param miles - Value in miles
 * @returns Value in kilometers
 */
export function milesToKm(miles: number): number {
    return miles * 1.60934;
}

/**
 * Convert kilometers to latitude degrees
 * @param km - Value in kilometers
 * @returns Approximate latitude degrees
 */
export function kmToLatitude(km: number): number {
    // Approximate conversion: 1 degree of latitude ≈ 111 km
    return km / 111;
}

/**
 * Convert kilometers to longitude degrees at a given latitude
 * @param km - Value in kilometers
 * @param latitude - Latitude in degrees
 * @returns Approximate longitude degrees
 */
export function kmToLongitude(km: number, latitude: number): number {
    // Longitude degrees vary by latitude
    // 1 degree of longitude ≈ 111 km * cos(latitude in radians)
    const latRad = latitude * (Math.PI / 180);
    const degreesPerKm = 111 * Math.cos(latRad);
    return km / degreesPerKm;
}

//      MAFS
const twoPies = Math.PI * 2

export function degToRadian(degrees: number): number {
    return (degrees / 360) * twoPies
}