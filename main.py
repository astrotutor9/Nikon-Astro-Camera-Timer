from machine import Pin
from time import sleep

relay = Pin(15, Pin.OUT)

relay.value(1)
sleep(0.25)
relay.value(0)
