# EarthPointer Development Plan V2

## Setup Tasks
1. **Project Initialization**
   - Verify Vite and Bun are installed
   - Ensure React, TailwindCSS, and Zustand are configured
   - Confirm Three.js and React-three-fiber are integrated

2. **Environment Setup**

## Utility Development (State-Agnostic)
1. **Coordinate Conversion Utilities**
   - Implement GPS to spherical coordinate conversion
   - Implement spherical to Cartesian coordinate conversion
   - Add unit tests for coordinate conversions

2. **Earth Geometry Utilities**
   - Create functions to generate latitude/longitude lines
   - Implement continent wireframe generation
   - Add city marker placement logic for specific French cities

3. **Visual Utilities**
   - Create fixed-size point renderer for Observer and airplane markers
   - Implement fixed-width line renderer for connections

## Functional Development

### Core 3D Scene
0. **3D Scene**
   Create a 3D scene for the app and ensure that it's framerate is capped to 144 FPS

1. **Earth Representation**
   - Create Earth sphere with a light grey texture
   - Add latitude/longitude lines
   - Implement continent wireframe
   - Add city markers for: Toulouse, Montauban, Pau, Royan, Paris, Lyon, Marseille, Bordeaux

2. **Observer Point**
   - Add observer point marker with fixed size
   - Implement observer position update logic
   - Set default coordinates to Toulouse (43.6047° N, 1.4442° E)

3. **Camera Controls**
   - Set up orbit controls for globe rotation
   - Implement zoom functionality
   - Add initial spinning animation
   - Configure frame rate limit

### Sidebar Functionality
1. **Main Sidebar**
   - Design input fields for GPS coordinates
   - Implement coordinate validation
   - Add mode selection buttons (disabled until coordinates entered)

2. **Secondary Sidebar (Airplane Mode)**
   - Create flight ID list display
   - Implement flight selection logic
   - Add airplane position marker with fixed size

### Mode Implementation
1. **Observer to Airplane Mode**
   - Create mock flight data (European flights only, realistic altitudes)
   - Implement flight selection handler
   - Add airplane position marker in 3D space with accurate altitude
   - Draw connecting line from observer to airplane with fixed width

### User Flow Implementation
1. **Initial State**
   - Implement spinning globe on load centered on Toulouse
   - Add coordinate input handling
   - Implement zoom-to-observer functionality

2. **Mode Switching**
   - Enable mode buttons after valid coordinate input
   - Implement secondary sidebar toggle
   - Handle flight selection events
   - Update 3D scene with airplane marker and connection line