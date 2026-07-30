import { useMemo } from 'react'
import * as THREE from 'three'
import { kmToSceneUnits } from '../utilities/unitConversions'

export const EarthCities = () => {
  const cities = useMemo(() => {
    const group = new THREE.Group()
    
    
    // French cities with their approximate GPS coordinates
    const cityData = [
      { name: 'Toulouse', lat: 43.6047, lon: 1.4442 },
      { name: 'Montauban', lat: 44.0167, lon: 1.3500 },
      { name: 'Pau', lat: 43.3000, lon: -0.3667 },
      { name: 'Royan', lat: 45.6267, lon: -1.0200 },
      { name: 'Paris', lat: 48.8566, lon: 2.3522 },
      { name: 'Lyon', lat: 45.7640, lon: 4.8357 },
      { name: 'Marseille', lat: 43.2965, lon: 5.3698 },
      { name: 'Bordeaux', lat: 44.8378, lon: -0.5792 }
    ]
    
    // Create a canvas for text rendering
    const canvas = document.createElement('canvas')
    const context = canvas.getContext('2d')
    canvas.width = 256
    canvas.height = 128
    
    if (context) {
      context.font = 'Bold 20px Arial'
      context.fillStyle = 'white'
      context.textAlign = 'center'
      context.textBaseline = 'middle'
    }
    
    cityData.forEach(city => {
      // Convert GPS coordinates to 3D position on sphere
      const radius = 5 // City distance to earth center
      const latRad = THREE.MathUtils.degToRad(city.lat)
      const lonRad = THREE.MathUtils.degToRad(city.lon)
      
      const x = radius * Math.cos(latRad) * Math.sin(lonRad)
      const y = radius * Math.sin(latRad)
      const z = radius * Math.cos(latRad) * Math.cos(lonRad)
      
      const position = new THREE.Vector3(x, y, z)
      const quaternion = new THREE.Quaternion().setFromUnitVectors(
        new THREE.Vector3(0, 0, 1),
        position.clone().negate().normalize()
      )

      const cityMaterial = new THREE.MeshBasicMaterial({ color: 0xff0000, side: THREE.DoubleSide })
      cityMaterial.polygonOffset = true
      cityMaterial.depthTest = false
      const cityMarker = new THREE.Mesh(
        new THREE.CircleGeometry(kmToSceneUnits(5), 32),
        cityMaterial
      )
      
      cityMarker.position.copy(position)
      cityMarker.quaternion.copy(quaternion)
      group.add(cityMarker)
      
      // Create city name label using sprite
      if (context) {
        // Clear canvas
        context.clearRect(0, 0, canvas.width, canvas.height)
        
        // Draw city name
        // context.fillText(city.name, canvas.width / 2, canvas.height / 2)
        
        // Create texture from canvas
        const texture = new THREE.CanvasTexture(canvas)
        
        // Create sprite material
        const spriteMaterial = new THREE.SpriteMaterial({ map: texture })
        
        // Create sprite
        const sprite = new THREE.Sprite(spriteMaterial)
        sprite.position.set(x, y + 0.3, z) // Position above the marker
        sprite.scale.set(0.5, 0.25, 1) // Adjust size
        
        group.add(sprite)
      }
    })
    
    return group
  }, [])
  
  return <primitive object={cities} />
}
