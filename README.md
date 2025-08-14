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
switches are wired together permanently other functions on the camera can not be used.
A new double relay was purchased to take the place of the two presses.

## Second Issue
The longer the exposure made the longer the read time of the exposure from the sensor
chip. There needs to be a variable delay between exposures to account for this changing
read/write timing. An LDR sensor reading the brightness of an LED than illuminates
whilst the read/write process is in operation might sort this.

## Completed
The LDR was not required as the camera resets to be able to take images almost immediately whilst still saving the previous image. A pause of 100 milliseconds is sufficient between exposures.

The double relay operates the camera perfectly. By closing the first relay for auto-focus and then shortly after closing the second for the exposure the exposure will start or stop. A simple RGB LED was added to the circuit to show red during an exposure and green otherwise. During a long exposure at night it might be easy to forget where the sequence is. Though a counter is added to the app display.

A simple web page was created to handle the exposures. The exposure time and number of exposures are adjusted with arrows. The exposure time jumps in useful steps. There is also a cancel button to stop the exposure if the exposure is in progress or about to be. This may be used if the weather closes in. There is also an exposure counter to indicate where the script is within the current run.

A cardboard case for the electronics has been made for the first real test. A 3D printed case will hopefully follow.