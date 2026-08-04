import { useState } from 'react'
import { useStore } from '../../store/useStore'
import { animateCameraFocus, focusCameraOnGPS } from '@/utilities/cameraUtils'

type Coordinates = {
  latitude: number
  longitude: number
  baro_altitude: number
}

type ObserverPositionFormProps = {
  onPositionUpdate?: (position: Coordinates) => void
  onFocusPosition?: () => void
}

export const ObserverPositionForm = ({ onFocusPosition }: ObserverPositionFormProps) => {
  const observerPosition = useStore(state => state.observerPosition)
  const setObserverPosition = useStore(state => state.setObserverPosition)
  const cameraControls = useStore(state => state.controls)
  
  const [latitude, setLatitude] = useState(observerPosition?.latitude || 0)
  const [longitude, setLongitude] = useState(observerPosition?.longitude || 0)
  const [baroalt, setBaroalt] = useState(observerPosition?.baro_altitude || 0)
  const [isValid, setIsValid] = useState(true)

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()

    const lat = latitude
    const lon = longitude
    const baro_alt = baroalt

    // Basic validation
    if (isNaN(lat) || isNaN(lon) || lat < -90 || lat > 90 || lon < -180 || lon > 180) {
      setIsValid(false)
      return
    }

    setIsValid(true)
    const newPosition = { latitude: lat, longitude: lon, baro_altitude: baro_alt }
    setObserverPosition(newPosition)
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <table className="w-full text-sm">
        <tbody>
          <tr>
            <td className="py-2 pr-4 text-right font-medium">
              <label htmlFor="latitude">Latitude</label>
            </td>
            <td className="py-2">
              <input
                type="text"
                id="latitude"
                value={latitude}
                onChange={(e) => setLatitude(parseFloat(e.target.value))}
                className={`w-full px-3 py-2 border rounded-md ${!isValid ? 'border-red-500' : 'border-gray-300'}`}
                placeholder="e.g. 43.6047"
              />
            </td>
          </tr>
          <tr>
            <td className="py-2 pr-4 text-right font-medium">
              <label htmlFor="longitude">Longitude</label>
            </td>
            <td className="py-2">
              <input
                type="text"
                id="longitude"
                value={longitude}
                onChange={(e) => setLongitude(parseFloat(e.target.value))}
                className={`w-full px-3 py-2 border rounded-md ${!isValid ? 'border-red-500' : 'border-gray-300'}`}
                placeholder="e.g. 1.4442"
              />
            </td>
          </tr>
          <tr>
            <td className="py-2 pr-4 text-right font-medium">
              <label htmlFor="baroalt">Altitude</label>
            </td>
            <td className="py-2">
              <input
                type="text"
                id="baroalt"
                value={baroalt}
                onChange={(e) => setBaroalt(parseFloat(e.target.value))}
                className={`w-full px-3 py-2 border rounded-md ${!isValid ? 'border-red-500' : 'border-gray-300'}`}
                placeholder="e.g. 50"
              />
            </td>
          </tr>
        </tbody>
      </table>

      {!isValid && (
        <p className="text-red-500 text-sm">Please enter valid GPS coordinates</p>
      )}

      <div className="flex gap-2">
        <button
          type="submit"
          className="flex-1 bg-sidebar-primary text-sidebar-primary-foreground py-2 px-4 rounded-md hover:bg-opacity-90 transition-colors"
        >
          Update Position
        </button>
        {observerPosition && (
          <button
            type="button"
            onClick={() => {
              if (!cameraControls) {
                console.error('Camera controls not available - cannot focus on observer position')
                return
              }
              if (!observerPosition) {
                console.error('Observer position not available - cannot focus camera')
                return
              }
              const targetPosition = focusCameraOnGPS(
                cameraControls,
                observerPosition.latitude,
                observerPosition.longitude,
                observerPosition.baro_altitude
              )
              animateCameraFocus(cameraControls, targetPosition, 1000)
            }}
            className="bg-sidebar-accent text-sidebar-accent-foreground py-2 px-4 rounded-md hover:bg-opacity-90 transition-colors flex items-center justify-center"
            title="Focus camera on observer position"
          >
            📍
          </button>
        )}
      </div>
    </form>
  )
}