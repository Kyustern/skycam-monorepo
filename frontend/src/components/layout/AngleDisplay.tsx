import { useEffect, useMemo, useRef } from 'react'
import { useStore } from '../../store/useStore'
import { computeAngles, formatAngle, formatAngleDisplay } from '../../utilities/angleUtils'
import { sendMovetoCommand } from '@/services/serialService'

export const AngleDisplay = () => {
  const observerPosition = useStore(state => state.observerPosition)
  const selectedFlight = useStore(state => state.selectedFlight)
  const socket = useStore(state => state.socket)
  const predictions = useStore(state => state.predictions)
  const socketReadyState = useStore(state => state.socketReadyState)
  
  const { signedAzimuth, verticalAngle } = useMemo(() => {
    if (!observerPosition || !selectedFlight || !predictions[selectedFlight?.callsign]) {
      return { signedAzimuth: 0, verticalAngle: 0 }
    }
    const target = predictions[selectedFlight.callsign] || selectedFlight
    return computeAngles(observerPosition, target)
  }, [observerPosition, predictions, selectedFlight?.callsign])

  // Track previous values to avoid duplicate emits
  const prevAzimuth = useRef<number>(0)
  const prevElevation = useRef<number>(0)

  useEffect(() => {
    if (socketReadyState && socket &&
        (signedAzimuth !== prevAzimuth.current || verticalAngle !== prevElevation.current)) {
      socket.emit("moveto", { azimuth: signedAzimuth, elevation: verticalAngle })
      prevAzimuth.current = signedAzimuth
      prevElevation.current = verticalAngle
    }
  }, [signedAzimuth, verticalAngle, socketReadyState, socket])


  useEffect(() => {
    console.log('LTES - predictions', predictions);

  }, [predictions])
  if (!observerPosition || !selectedFlight) return null

  return (
    <div className="bg-black/70 text-white p-2 rounded text-xs font-mono">
      <div>
        <span style={{ color: '#facc15' }}>Azimuth: </span>
        <span style={{ color: '#facc15' }}>{signedAzimuth}</span>
      </div>
      <div>
        <span style={{ color: '#38bdf8' }}>Vertical: </span>
        <span style={{ color: '#38bdf8' }}>{verticalAngle}</span>
      </div>
    </div>
  )
}
