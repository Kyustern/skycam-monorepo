import { OrbitControls, Stars } from "@react-three/drei"
import { Canvas, useLoader } from "@react-three/fiber"
import { useRef, useEffect, useMemo } from "react"
import type { OrbitControls as OrbitControlsImpl } from 'three-stdlib'
import { useStore } from "../../store/useStore"
import { AirplaneMarker } from "../AirplaneMarker"
import { PredictionMarker } from "../PredictionMarker"
import { AzimuthAngleOverlay } from "../AzimuthAngleOverlay"
import { ConnectionLine } from "../ConnectionLine"
import { EarthCities } from "../EarthCities"
import { EarthGrid } from "../EarthGrid"
import { ObserverMarker } from "../ObserverMarker"
import { AngleDisplay } from "../layout/AngleDisplay"
import { HumidityVisibilityDisplay } from "../layout/HumidityVisibilityDisplay"
import { ZoomControl } from "../layout/ZoomControl"
import * as THREE from 'three'
import { kmToSceneUnits } from "@/utilities/unitConversions"
import { TextureLoader } from 'three'
import { AxesHelper } from "../AxesHelper"

// Earth mesh component with texture
const EarthMesh = ({ children }: { children: React.ReactNode }) => {
    const earthRef = useRef<THREE.Group>(null)
    //     useFrame(() => {
    //     if (earthRef.current) {
    //       // earthRef.current.rotation.y += 0.001
    //     }
    //   })

    const earthTexture = useLoader(TextureLoader, "assets/3d/textures/world.200401.3x21600x10800.jpg")
    return (
        // <group ref={earthRef}>
        <group>
            <AxesHelper />
            {children}
            <mesh rotation={[0, (Math.PI / 2) * 3, 0]}>
                <sphereGeometry args={[5, 128, 128]} />
                <meshBasicMaterial map={earthTexture} />
            </mesh>
        </group>
    )
}

const GradientBackground = ({ darknessMultiplier }: { darknessMultiplier: number }) => {
    const texture = useMemo(() => {
        const canvas = document.createElement('canvas')
        canvas.width = 2
        canvas.height = 512
        const ctx = canvas.getContext('2d')!

        const color1 = new THREE.Color(0xff9966)
        const color2 = new THREE.Color(0xff5e1a)
        const color3 = new THREE.Color(0x1a1a2e)

        color1.multiplyScalar(darknessMultiplier)
        color2.multiplyScalar(darknessMultiplier)
        color3.multiplyScalar(darknessMultiplier)

        const gradient = ctx.createLinearGradient(0, 0, 0, 512)
        gradient.addColorStop(0, `#${color1.getHexString()}`)
        gradient.addColorStop(0.5, `#${color2.getHexString()}`)
        gradient.addColorStop(1, `#${color3.getHexString()}`)
        ctx.fillStyle = gradient
        ctx.fillRect(0, 0, 2, 512)

        const texture = new THREE.CanvasTexture(canvas)
        texture.magFilter = THREE.LinearFilter
        return texture
    }, [darknessMultiplier])

    useEffect(() => {
        return () => {
            texture.dispose()
        }
    }, [texture])

    return <primitive attach="background" object={texture} />
}

type MainSceneProps = {
    controlsRef: React.RefObject<OrbitControlsImpl | null>
}

export const MainScene = ({ controlsRef }: MainSceneProps) => {
    const darkness = useStore(state => state.darkness)
    const setControls = useStore(state => state.setControls)

    useEffect(() => {
        if (controlsRef.current) {
            setControls(controlsRef.current)
        }
    },
        [setControls, controlsRef, controlsRef.current])

    const cameraDistances: { minDistance: number, maxDistance: number } = useMemo(() => {
        return { minDistance: kmToSceneUnits(1), maxDistance: 10 }
    }, [])

    return (
        <div className="h-full relative">

            <Canvas
                camera={{ position: [0, 0, 10], fov: 50, rotation: [0, 0, 0], near: 0.01, far: 100 }}
                onCreated={({ gl }) => {
                    gl.setAnimationLoop(null)
                    const animate = () => {
                        controlsRef.current?.update()
                        requestAnimationFrame(animate)
                    }
                    animate()
                }}>
                <GradientBackground darknessMultiplier={darkness} />
                <ambientLight intensity={1} />
                <pointLight position={[10, 10, 10]} />
                    <EarthMesh>
                    <EarthGrid />
                    <EarthCities />
                    <ObserverMarker />
                    <AirplaneMarker />
                    <PredictionMarker />
                    <ConnectionLine />
                    <AzimuthAngleOverlay />
                    </EarthMesh>
                <OrbitControls
                    ref={controlsRef}
                    enableDamping
                    dampingFactor={0.060}
                    minDistance={cameraDistances.minDistance}
                    maxDistance={cameraDistances.maxDistance}
                />
                <Stars radius={100} depth={50} count={5000} factor={4} saturation={0} fade speed={1} />
            </Canvas>
            <div className="absolute bottom-4 right-4 flex items-center gap-2">
                <HumidityVisibilityDisplay />
                <AngleDisplay />
                <ZoomControl controlsRef={controlsRef} zoomStep={5} />
                <div className="bg-black/70 text-white p-2 rounded text-xs font-mono">
                    {/* Camera: ({controlsRef.current.}, {cameraPos.y.toFixed(2)}, {cameraPos.z.toFixed(2)}) */}
                </div>
            </div>
        </div>
    )
}
