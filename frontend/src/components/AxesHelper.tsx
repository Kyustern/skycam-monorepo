import { degToRadian } from '@/utilities/conversions'
import { kmToSceneUnits } from '@/utilities/unitConversions'
import { Text } from '@react-three/drei'
import { useMemo } from 'react'
import * as THREE from 'three'
import { degToRad } from 'three/src/math/MathUtils.js'

const AXIS_RADIUS = 10

const axisConfig = [
  { direction: [1, 0, 0] as [number, number, number], color: 'red', label: 'X' },
  { direction: [0, 1, 0] as [number, number, number], color: 'green', label: 'Y' },
  { direction: [0, 0, 1] as [number, number, number], color: 'blue', label: 'Z' },
]

export const AxesHelper = () => {
  return (
    <group>
      {axisConfig.map((axis) => (
        <Axis 
          key={axis.label} 
          direction={axis.direction} 
          color={axis.color} 
          label={axis.label} 
          length={AXIS_RADIUS}
        />
      ))}
    </group>
  )
}

interface AxisProps {
  direction: [number, number, number]
  color: string
  label: string
  length: number
}

const Axis = ({ direction, color, label, length }: AxisProps) => {
  const [dx, dy, dz] = direction
  
  // Position at the tip of the axis
  const tipPosition: [number, number, number] = [
    dx * length,
    dy * length,
    dz * length
  ]
  
  // Line object
  const line = useMemo(() => {
    const points = [
      new THREE.Vector3(0, 0, 0),
      new THREE.Vector3(dx * length, dy * length, dz * length)
    ]
    const geometry = new THREE.BufferGeometry().setFromPoints(points)
    const material = new THREE.LineBasicMaterial({ color: color, linewidth: 2 })
    return new THREE.Line(geometry, material)
  }, [dx, dy, dz, length, color])
  
  // Cone orientation: rotate to point along the axis
  const coneRotation = useMemo(() => {
    if (dx === 1) {
      return [0, 0, degToRadian(90)]
    } else if (dx === -1) {
      return [0, 0, degToRadian(90 + 180)]
    } else if (dy === 1) {
      return [degToRad(180), 0, 0]
    } else if (dy === -1) {
      return [0, 0, 0]
    } else if (dz === 1) {
      return [degToRad(-90), 0, 0]
    } else if (dz === -1) {
      return [degToRad(90), 0, 0]
    }
    return [0, 0, 0]
  }, [dx, dy, dz])
  
  // Label position: slightly offset from the tip towards the origin
  const labelPosition = useMemo(() => [
    dx * (length - 0.8),
    dy * (length - 0.8),
    dz * (length - 0.8)
  ] as [number, number, number], [dx, dy, dz, length])
  
  return (
    <group>
      {/* Axis line */}
      <primitive object={line} />
      
      {/* Cone at the tip */}
      <mesh position={tipPosition} rotation={coneRotation as [number, number, number]}>
        <coneGeometry args={[kmToSceneUnits(100), kmToSceneUnits(200), 32]} />
        <meshStandardMaterial color={color} />
      </mesh>
      
      {/* Label with colored background */}
      <Label position={labelPosition} rotation={coneRotation} color={color} text={label} />
    </group>
  )
}

interface LabelProps {
  position: [number, number, number]
  rotation: [number, number, number]
  color: string
  text: string
}

const Label = ({ position, color, text, rotation }: LabelProps) => {
  return (
    <group position={position}>
      {/* Background plane */}
      <mesh position={[0, 0, -0.01]} rotation={rotation}>
        <circleGeometry args={[kmToSceneUnits(100), 32, 0, Math.PI * 2]} />
        <meshStandardMaterial color={color} side={THREE.DoubleSide} />
      </mesh>
      {/* Text */}
      <Text 
        position={[0, 0, 0.01]}
        rotation={rotation}
        fontSize={0.4}
        color="white"
        anchorX="center"
        anchorY="middle"
      >
        {text}
      </Text>
    </group>
  )
}
