import { useRef, useEffect } from 'react'
import * as THREE from 'three'
import { useThree } from '@react-three/fiber'

export const EarthGrid = () => {
  const { camera } = useThree()
  const gridRef = useRef<THREE.Group>(null)
  
  useEffect(() => {

    if (!gridRef.current) return
    
    // Clear existing grid lines
    while (gridRef.current.children.length > 0) {
      gridRef.current.remove(gridRef.current.children[0])
    }
    
    // Calculate zoom level based on camera distance from earth (radius = 5)
    const distanceFromEarth = camera.position.length()
    const zoomLevel = Math.max(1, Math.min(10, 40 / distanceFromEarth))
    
    // Adjust grid density based on zoom level
    const latStep = Math.max(5, 40 / zoomLevel)
    const lonStep = Math.max(5, 40 / zoomLevel)
    const latLineStep = Math.max(2, 10 / zoomLevel)
    const lonLineStep = Math.max(2, 10 / zoomLevel)
    
    // Create latitude lines (horizontal)
    for (let lat = -80; lat <= 80; lat += latStep) {
      const radius = 5 * Math.cos(THREE.MathUtils.degToRad(lat))
      const height = 5 * Math.sin(THREE.MathUtils.degToRad(lat))
      
      const points = []
      for (let lon = -180; lon <= 180; lon += lonLineStep) {
        const x = radius * Math.sin(THREE.MathUtils.degToRad(lon))
        const y = height
        const z = radius * Math.cos(THREE.MathUtils.degToRad(lon))
        points.push(new THREE.Vector3(x, y, z))
      }
      
      const geometry = new THREE.BufferGeometry().setFromPoints(points)
      const material = new THREE.LineBasicMaterial({ color: 0x888888, transparent: true, opacity: 0.4 })
      const line = new THREE.Line(geometry, material)
      gridRef.current.add(line)
    }
    
    // Create longitude lines (vertical)
    for (let lon = -180; lon <= 180; lon += lonStep) {
      const points = []
      for (let lat = -90; lat <= 90; lat += latLineStep) {
        const radius = 5 * Math.cos(THREE.MathUtils.degToRad(lat))
        const height = 5 * Math.sin(THREE.MathUtils.degToRad(lat))
        const x = radius * Math.sin(THREE.MathUtils.degToRad(lon))
        const y = height
        const z = radius * Math.cos(THREE.MathUtils.degToRad(lon))
        points.push(new THREE.Vector3(x, y, z))
      }
      
      const geometry = new THREE.BufferGeometry().setFromPoints(points)
      const material = new THREE.LineBasicMaterial({ color: 0x888888, transparent: true, opacity: 0.4 })
      const line = new THREE.Line(geometry, material)
      gridRef.current.add(line)
    }
    console.log("camera.position", camera.position);
  }, [camera.position])
  
  return <mesh>
    <group ref={gridRef} />
  </mesh>
}
