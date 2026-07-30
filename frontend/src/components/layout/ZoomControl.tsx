import type { OrbitControls as OrbitControlsImpl } from 'three-stdlib'

type ZoomControlProps = {
  controlsRef: React.RefObject<OrbitControlsImpl | null>
  zoomStep?: number
}

export const ZoomControl = ({
  controlsRef,
  zoomStep = 5,
}: ZoomControlProps) => {
  const handleZoomIn = () => {
    if (controlsRef.current) {
      controlsRef.current.dollyIn(zoomStep)
      controlsRef.current.update()
    }
  }

  const handleZoomOut = () => {
    if (controlsRef.current) {
      controlsRef.current.dollyOut(zoomStep)
      controlsRef.current.update()
    }
  }

  const handleReset = () => {
    if (controlsRef.current) {
      const defaultDistance = 10
      const currentDistance = controlsRef.current.getDistance()
      const delta = currentDistance - defaultDistance

      if (delta > 0) {
        controlsRef.current.dollyOut(-delta)
      } else {
        controlsRef.current.dollyIn(-delta)
      }
      controlsRef.current.update()
    }
  }

  return (
    <div className="bg-black/70 text-white p-2 rounded flex gap-2 items-center">
      <button
        onClick={handleZoomIn}
        className="px-3 py-1 bg-blue-600 hover:bg-blue-700 rounded text-sm font-mono transition-colors"
      >
        +
      </button>
      <button
        onClick={handleZoomOut}
        className="px-3 py-1 bg-blue-600 hover:bg-blue-700 rounded text-sm font-mono transition-colors"
      >
        -
      </button>
      <button
        onClick={handleReset}
        className="px-3 py-1 bg-gray-600 hover:bg-gray-700 rounded text-sm font-mono transition-colors"
      >
        Reset
      </button>
    </div>
  )
}
