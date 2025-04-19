# Nikon-Astro-Camera-Timer
A remote timing control using a Pi Pico to automate very long exposures on a Nikon D3300

A purchased manual timer from eBay utilises two presses to initiate an exposure. The first
starts the auto-focus, the second starts the exposure.

In astrophotography the manual remote when used in conjunction with the 'T' setting
will start the exposure on the first full press and stop on the second. The intention here
is to replace the manual press with a timer controlled by a Raspberry Pi Pico using
a relay to make the presses that the camera expects.

## First Issue
The remote uses the two switches. A single relay can not be used as the first press
needs to be made before the second. Though the auto-focus is not being used if the
switches are wired to gether permanently other functions on the camera can not be used.
A new double relay was purchased to take the place of the two presses.

## Second Issue
The longer the exposure made the longer the read time of the exposure from the sensor
chip. There needs to be a variable delay between exposures to account for this changing
read/write timing. An LDR sensor reading the brightness of an LED than illuminates
whilst the read/write process is in operation might sort this.