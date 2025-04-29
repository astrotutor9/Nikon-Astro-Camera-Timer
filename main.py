from machine import Pin
from time import sleep, time

FOCUS_RELAY = Pin(15, Pin.OUT)
SHUTTER_RELAY = Pin(14, Pin.OUT)

# Using an LED as shutter open or closed
LED = Pin(13, Pin.OUT)
LED.value(0)

setting_up = True

exposure_length_seconds = 0
number_of_exposures = 0
counted_exposures = 0
exposure = False

time_now = 0

# This needs to be verified on camera
# Length may change in relation to exposure length
sdCard_write_time = 1

def get_exposure_settings():
    exposure_time = int(input("What is the exposure time in seconds? "))
    how_many = int(input("How many images? "))
    return exposure_time, how_many

def remote_release():
    FOCUS_RELAY.value(1)
    SHUTTER_RELAY.value(1)
    sleep(0.1)
    SHUTTER_RELAY.value(0)
    FOCUS_RELAY.value(0)

SHUTTER_RELAY.value(0)
FOCUS_RELAY.value(0)

while True:
    if setting_up:
        exposure_length_seconds, number_of_exposures = get_exposure_settings()
        setting_up = False
        
    if exposure == False and (counted_exposures < number_of_exposures):
        start_time = time()
        print("Started exposure")
        exposure = True
        counted_exposures += 1
        LED.value(not LED.value())
        remote_release()
        
    if exposure == True and ((time() - start_time) >= exposure_length_seconds):
        remote_release()
        LED.value(not LED.value())
        print("Ended exposure")
        sleep(sdCard_write_time)        
        exposure = False
        
    if counted_exposures == number_of_exposures and exposure == False:
        setting_up = True
        counted_exposures = 0
        print("Reset for next exposure")
        

    


