# EarthPointer Development Plan

## Setup Tasks
1. **Project Initialization**
   - Verify Vite and Bun are installed
   - Ensure TypeScript, React, TailwindCSS, and Zustand are configured
   - Confirm Three.js and React-three-fiber are integrated

2. **Environment Setup**
   - Install dependencies: `bun add vite react react-dom tailwindcss zustand three @react-three/fiber`
   - Configure TailwindCSS for the project
   - Set up TypeScript configuration

## Utility Development (State-Agnostic)
1. **Coordinate Conversion Utilities**
   - Implement GPS to spherical coordinate conversion
   - Implement spherical to Cartesian coordinate conversion
   - Add unit tests for coordinate conversions

2. **Earth Geometry Utilities**
   - Create functions to generate latitude/longitude lines
   - Implement continent wireframe generation
   - Add city marker placement logic

## Functional Development

### Core 3D Scene
1. **Earth Representation**
   - Create Earth sphere with texture
   - Add latitude/longitude lines
   - Implement continent wireframe
   - Add city markers for French cities

2. **Observer Point**
   - Add observer point marker
   - Implement observer position update logic

3. **Camera Controls**
   - Set up orbit controls for globe rotation
   - Implement zoom functionality
   - Add initial spinning animation

### Sidebar Functionality
1. **Main Sidebar**
   - Design input fields for GPS coordinates
   - Implement coordinate validation
   - Add mode selection buttons

2. **Secondary Sidebar (Airplane Mode)**
   - Create flight ID list display
   - Implement flight selection logic
   - Add airplane position marker

### Mode Implementation
1. **Observer to Airplane Mode**
   - Create mock flight data (European flights only)
   - Implement flight selection handler
   - Add airplane position marker in 3D space
   - Draw connecting line from observer to airplane

### User Flow Implementation
1. **Initial State**
   - Implement spinning globe on load
   - Add coordinate input handling
   - Implement zoom-to-observer functionality

2. **Mode Switching**
   - Enable mode buttons after coordinate input
   - Implement secondary sidebar toggle
   - Handle flight selection events

## Testing Plan
1. **Unit Tests**
   - Coordinate conversion functions
   - Geometry generation utilities

2. **Integration Tests**
   - Sidebar coordinate input flow
   - Mode switching functionality
   - 3D scene rendering

3. **User Acceptance Testing**
   - Verify initial spinning behavior
   - Test coordinate input and zoom
   - Validate airplane mode functionality

## Questions for Clarification
1. Should the airplane altitude be visually scaled for better visibility?
   No, the airplane altitude must remain to scale relative to the representation of the earth. However you can give to both the point representing the Observer and the point representing the airplane a fixed size, so they can easily be seen by the user regardless of the zoom level.
2. Are there specific French cities that should be prioritized for markers?
   Yes, Toulouse, Montauban, Pau, Royan are on my list. Don't forget the other major ones (Paris, Lyon, Marseille and Bordeaux)
3. What should be the default observer coordinates on initial load?
   The default coordinates should point to Toulouse
4. Should the connecting line between observer and airplane have any visual properties (color, thickness)?
   Same as the Observer and airplane, the line should have a fixed width so it can be seen regardless of the zoom level.
5. Are there any specific performance considerations for the 3D rendering?
   The frame rate should be capped at 144 FPS

