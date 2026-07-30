import { useMemo } from 'react'
import * as THREE from 'three'

export const EarthContinents = () => {
  const continentLines = useMemo(() => {
    const group = new THREE.Group()
    
    // Simplified continent outlines (this would be more detailed in a real app)
    // Europe
    const europePoints = [
      new THREE.Vector3(3, 1, 2),  // Approximate coordinates
      new THREE.Vector3(2.5, 0.5, 2.5),
      new THREE.Vector3(2, 0, 2),
      new THREE.Vector3(1.5, -0.5, 1.5),
      new THREE.Vector3(1, -1, 1),
    ]
    
    // Africa
    const africaPoints = [
      new THREE.Vector3(0, -1, 2),
      new THREE.Vector3(-1, -2, 1),
      new THREE.Vector3(-2, -3, 0),
      new THREE.Vector3(-1, -4, -1),
      new THREE.Vector3(0, -5, -2),
    ]
    
    // Asia
    const asiaPoints = [
      new THREE.Vector3(4, 0, 1),
      new THREE.Vector3(4.5, -1, 0.5),
      new THREE.Vector3(4, -2, 0),
      new THREE.Vector3(3, -3, -1),
    ]
    
    // North America
    const northAmericaPoints = [
      new THREE.Vector3(-3, 1, 1),
      new THREE.Vector3(-4, 0, 0),
      new THREE.Vector3(-4.5, -1, -1),
      new THREE.Vector3(-4, -2, -2),
    ]
    
    // South America
    const southAmericaPoints = [
      new THREE.Vector3(-2, -2, 1),
      new THREE.Vector3(-3, -3, 0),
      new THREE.Vector3(-3.5, -4, -1),
      new THREE.Vector3(-3, -5, -2),
    ]
    
    const createContinentLine = (points: THREE.Vector3[]) => {
      const geometry = new THREE.BufferGeometry().setFromPoints(points)
      const material = new THREE.LineBasicMaterial({ color: 0xffffff, linewidth: 2 })
      return new THREE.Line(geometry, material)
    }
    
    group.add(createContinentLine(europePoints))
    group.add(createContinentLine(africaPoints))
    group.add(createContinentLine(asiaPoints))
    group.add(createContinentLine(northAmericaPoints))
    group.add(createContinentLine(southAmericaPoints))
    
    return group
  }, [])
  
  return <primitive object={continentLines} />
}