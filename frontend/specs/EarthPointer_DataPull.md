I want you to build a very simple javascript script that pulls data from the ADS-B exchange API. The data itself would be a snapshot of ADS-B data that lists all airplanes within a 200km radius around GPS coordinates which would be given as an input to the script.

The script should then format the data to output a JSON document, which will contain an object with as keys the flight ids of each detected aircrafts and as value to a key the associated GPS coordinates for the flight id.

The script should be written from the bun runtime.