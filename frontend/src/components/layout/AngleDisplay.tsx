import { useMemo } from 'react'
import { useStore } from '../../store/useStore'
import { computeAngles, formatAngle } from '../../utilities/angleUtils'
import { sendMovetoCommand } from '@/services/serialService'

export const AngleDisplay = () => {
  const observerPosition = useStore(state => state.observerPosition)
  const selectedFlight = useStore(state => state.selectedFlight)

  const { signedAzimuth, verticalAngle } = useMemo(() => {
    if (!observerPosition || !selectedFlight) {
      return { signedAzimuth: 0, verticalAngle: 0 }
    }
    const angles = computeAngles(observerPosition, selectedFlight)
    const formatedAngles = {
      signedAzimuth: formatAngle(angles.signedAzimuth),
      verticalAngle: formatAngle(angles.verticalAngle)
    }
    sendMovetoCommand({ azimuth: parseFloat(formatedAngles.signedAzimuth), elevation: parseFloat(formatedAngles.verticalAngle) })
    return formatedAngles
  }, [selectedFlight])

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
