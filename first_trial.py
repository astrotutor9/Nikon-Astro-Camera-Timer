# Discovered that two relays or Dual Pole Single Throw
# relay is needed. Two switches are in the remote.
# Initial press focuses, further press takes.
# But with focus initiated no camera control is possible.

from machine import Pin
from time import sleep

relay = Pin(15, Pin.OUT)

exposure_length_seconds = 5
number_of_exposures = 2

# This needs to be verified on camera
# Length may change in relation to exposure length
sdCard_write_time = 2

def remote_release():
    relay.value(1)
    sleep(0.25)
    relay.value(0)

# Start exposure wait exposure length
# Stop exposure wait for image to write to memory
for exposures in range(number_of_exposures):
    remote_release()               # exposure start
    sleep(exposure_length_seconds)
    remote_release()               # exposure stop
    sleep(sdCard_write_time)