import { useRef } from 'react'
import { useFrame } from '@react-three/fiber'
import * as THREE from 'three'
import { AxesHelper } from './AxesHelper'

export const SpinningEarth = ({ children }: { children: React.ReactNode }) => {
  const earthRef = useRef<THREE.Group>(null)
  
  useFrame(() => {
    if (earthRef.current) {
      // earthRef.current.rotation.y += 0.001
    }
  })
  
  return <group ref={earthRef}>
    <AxesHelper />
    {children}
  </group>
}