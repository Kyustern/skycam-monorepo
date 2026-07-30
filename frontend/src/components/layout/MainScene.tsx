import { OrbitControls, Stars } from "@react-three/drei"
import { Canvas } from "@react-three/fiber"
import { useRef, useEffect, useMemo } from "react"
import type { OrbitControls as OrbitControlsImpl } from 'three-stdlib'
import { useStore } from "../../store/useStore"
import { AirplaneMarker } from "../AirplaneMarker"
import { AzimuthAngleOverlay } from "../AzimuthAngleOverlay"
import { ConnectionLine } from "../ConnectionLine"
import { EarthCities } from "../EarthCities"
import { EarthGrid } from "../EarthGrid"
import { ObserverMarker } from "../ObserverMarker"
import { SpinningEarth } from "../SpinningEarth"
import { AngleDisplay } from "../layout/AngleDisplay"
import { HumidityVisibilityDisplay } from "../layout/HumidityVisibilityDisplay"
import { ZoomControl } from "../layout/ZoomControl"
import { focusCameraOnGPS, animateCameraFocus } from '../../utilities/cameraUtils'
import * as THREE from 'three'
import { kmToSceneUnits } from "@/utilities/unitConversions"
// extend({ ZoomControl })

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

export const MainScene = () => {
    const observerPosition = useStore(state => state.observerPosition)
    const selectedFlight = useStore(state => state.selectedFlight)
    const mode = useStore(state => state.selectionMode)
    const darkness = useStore(state => state.darkness)
    const setControls = useStore(state => state.setControls)
    const controlsRef = useRef<OrbitControlsImpl>(null)

    useEffect(() => {
        if (controlsRef.current) {
            setControls(controlsRef.current)
        }
    },
    [setControls, controlsRef])
    // Set default position to Toulouse
    // useEffect(() => {
    //     setObserverPosition({ latitude: 43.6047, longitude: 1.4442, baro_altitude: 150 })
    // }, [setObserverPosition])

    // Auto-focus camera based on observer position or selected flight
    useEffect(() => {
        if (controlsRef.current) {
            const timer = setTimeout(() => {
                if (mode === 'airplane' && selectedFlight) {
                    console.log("mode === 'airplane' && selectedFlight", mode === 'airplane' && selectedFlight);

                    // Focus on selected flight with smooth animation
                    animateCameraFocus(
                        controlsRef.current,
                        focusCameraOnGPS(controlsRef.current, selectedFlight.latitude, selectedFlight.longitude, observerPosition.baro_altitude)
                    )
                } else if (observerPosition) {
                    console.log("observerPosition", observerPosition);
                    animateCameraFocus(
                        controlsRef.current,
                        focusCameraOnGPS(controlsRef.current, observerPosition.latitude, observerPosition.longitude, observerPosition.baro_altitude)
                    )
                } else {
                    console.log("default")

                    // Default focus on Earth center
                    animateCameraFocus(controlsRef.current, new THREE.Vector3(0, 0, 0))
                }
            }, 500)
            return () => clearTimeout(timer)
        }
    }, [controlsRef, observerPosition, selectedFlight, mode])

    const cameraDistances: { minDistance: number, maxDistance: number } = useMemo(() => {
        if (observerPosition && !selectedFlight) {
            return { minDistance: 2, maxDistance: 30 }
        }
        if (observerPosition && selectedFlight) {
            return { minDistance: kmToSceneUnits(1), maxDistance: 2 }
        } else {
            return { minDistance: 10, maxDistance: 30 }

        }
    }, [observerPosition, selectedFlight])

    return (
        <div className="h-full relative">

            <Canvas 
                camera={{ position: [0, 0, 10], fov: 50, rotation: [0, 0, 0], near: 0.01, far: 100 }} 
                onCreated={({ gl }) => {
                gl.setAnimationLoop(null)
                const animate = () => {
                    controlsRef.current?.update()
                    // setCameraPos({
                    //     x: camera.position.x,
                    //     y: camera.position.y,
                    //     z: camera.position.z
                    // })
                    requestAnimationFrame(animate)
                }
                animate()
            }}>
                <GradientBackground darknessMultiplier={darkness} />
                <ambientLight intensity={0.5} />
                <pointLight position={[10, 10, 10]} />
                <SpinningEarth>
                    <mesh>
                        <sphereGeometry args={[5, 128, 128]} />
                        <meshStandardMaterial color="lightgrey" />
                    </mesh>
                    <EarthGrid />
                    {/* <EarthContinents /> */}
                    <EarthCities />
                    <ObserverMarker />
                    <AirplaneMarker />
                    <ConnectionLine />
                    <AzimuthAngleOverlay />
                </SpinningEarth>
                <OrbitControls
                    ref={controlsRef}
                    enableDamping
                    dampingFactor={0.010}
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
