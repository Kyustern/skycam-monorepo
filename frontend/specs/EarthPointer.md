## Overview

This spec file is here to describe the functional and technical aspects of EarthPointer, a web application that will mainly be used as a tool to visualize 3D space and more specifically an axis in 3D space that joins a flying or spatial object to Earth coordinates.

### Quick notes
If it is not clear enough, in those specs, the word Observer corresponds to a point on the earth surface.

### Functionality

The application will feature a 3D scene occupying most of the screen that would show a spherical approximation of the Earth. This representation of the earth will feature lines for each main latitude and longitude degrees, a 2D wireframe of the contients and a dot at the coordinates of the main cities in France, with the name of the city next to the point.

On the sphere, a point will be visible, marking the position of the Observer, from which the line of axis will start from.

Three modes will be available, one to see the axis from the Observer to an airplane, another to see the axis from the Observer to a satellite and finally one to see the axis from the Observer to the choosen spatial body from the solar system.

For this first sprint we will only implement the Oserver to airplane first, and to simplify things even further the available airplane positions will be mocked in the form of a list of imaginary yet plausible positions. All planes position should be within the European union and at realistic flight levels.

The application will feature a fixed sidebar on the left side of the screen that will allow the user to input the current position of the Observer, and to change between the three modes.

### Initial state user story

When the user loads the web application, the 3D scene starts and the earth representation starts slowly spinnings.

Once the user inputs correct GPS coordinates in the form of the main sidebar, the Earth stops rotating and the view zooms in to the coordinates of the point.

At all times the user should be able to rotate the globe by holding down the left click and dragging toward the right or left of the screen.

### Observer to airplane mode

As said previously, we will only implement the Observer to airplane mode for now. For this mode the user flow goes as following :

Once the Observer GPS coordinates are entered, the mode selection buttons become available. once the Observer to airplane button is clicked a secondary sidebar opens next to the main one, containing a list of fake flight ids and for each flight id its associated mocked GPS coordinates

Once the user clicks a flight ID, another dot appears high above the earth surface in 3D space, with its altitude represented accurately relatively to the earth representation size.

<!-- 
Not relevant anymore ! :
### Technical implementation

#### Tech stack

The app shall use Vite for the bundler, and Bun as its runtime. The current state of the app already implements those choices.

The application should be written in Typescript, use React, TailwindCSS, Zustand for state management.

To render out the 3D scene the application should use Three.js and React-three-fiber.

#### Coordinates system

While the coordinates of the observer and the airplanes comes in GPS format (latitude longitude and altitude), when the application has to store or represent an object in 3d space, it's coordinate will have to be converted to the radial (or spherical) coordinate system. Finally the coordinates will be converted for the right-handed cartesian coordinate system for ThreeJS. -->