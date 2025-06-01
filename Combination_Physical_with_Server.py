from machine import Pin
from time import sleep, time
import network
import socket
import ure

# Set up Pico Wi-Fi Access Point
ssid = 'Pico-AP'
password = '12345678'

ap = network.WLAN(network.AP_IF)
ap.config(essid=ssid, password=password)
ap.active(True)

while ap.active() == False:
  pass
print('Connection is successful')
print(ap.ifconfig())

# Set up connections for camera remote wiring
FOCUS_RELAY = Pin(15, Pin.OUT)
SHUTTER_RELAY = Pin(14, Pin.OUT)

# Using an LED as shutter open or closed
LED = Pin(13, Pin.OUT)
LED.value(0)

# Not making exposures if True
setting_up = True

exposure_length_seconds = 0
number_of_exposures = 0
counted_exposures = 0
exposure = False

time_now = 0

# This needs to be verified on camera
# Length may change in relation to exposure length
sdCard_write_time = 1

##################################################
# Functions
##################################################

# Simple HTTP response header
def response_header():
    return 'HTTP/1.0 200 OK\r\nContent-type: text/html\r\n\r\n'

# HTML/CSS webpage
def webpage(exposure_time=5, how_many=5):
    html = f"""
<!DOCTYPE html>
<html lang='en'>
<head>
<meta charset='UTF-8'>
<meta name='viewport' content='width=device-width, initial-scale=1.0'>
<title>Pico Control</title>
<style>
body {{ background-color: black; color: red; text-align: center; }}
.arrow {{ font-size: 80px; cursor: pointer; user-select: none; }}
.value {{ font-size: 50px; }}
button {{ font-size: 30px; margin-top: 20px; color: black; background-color: red; }}
p {{ font-size: 40px; margin-top: 0px; margin-bottom: 0px; }}
</style>
</head>
<body>
<form method='POST'>
  <div>
    <span class='arrow' onclick='update("time", 1)'>&#9650;</span>
    <div class='value' id='time'>{exposure_time}</div>
    <span class='arrow' onclick='update("time", -1)'>&#9660;</span>
    <input type='hidden' name='exposure_time' id='time_input' value='{exposure_time}'/>
    <p>Time</p>
  </div>
  <div>
    <span class='arrow' onclick='update("number", 1)'>&#9650;</span>
    <div class='value' id='number'>{how_many}</div>
    <span class='arrow' onclick='update("number", -1)'>&#9660;</span>
    <input type='hidden' name='how_many' id='number_input' value='{how_many}'/>
    <p>Number</p>
  </div>
  <button type='submit'>Submit</button>
</form>
<script>
function update(id, change) {{
  const limits = {{'time': [5, 300], 'number': [1, 100]}};
  let valElement = document.getElementById(id);
  let inputElement = document.getElementById(id + '_input');
  let val = parseInt(valElement.textContent);
  if (isNaN(val)) val = limits[id][0];
  val = Math.min(limits[id][1], Math.max(limits[id][0], val + change));
  valElement.textContent = val;
  inputElement.value = val;
}}
</script>
</body>
</html>
"""
    return html

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

# Ensure relays are open at the start
SHUTTER_RELAY.value(0)
FOCUS_RELAY.value(0)

# Start simple HTTP server
addr = socket.getaddrinfo('0.0.0.0', 80)[0][-1]
s = socket.socket()
s.bind(addr)
s.listen(1)

print('Server running at:', ap.ifconfig()[0])

# Server loop
exposure_time, how_many = 5, 5

while True:
    try:
        cl, addr = s.accept()
        request = cl.recv(1024).decode('utf-8')

        if 'POST' in request:
            exposure_match = ure.search(r"exposure_time=(\d+)", request)
            number_match = ure.search(r"how_many=(\d+)", request)

            if exposure_match and number_match:
                exposure_time = int(exposure_match.group(1))
                how_many = int(number_match.group(1))
                print('Received: exposure_time={}, how_many={}'.format(exposure_time, how_many))

        response = response_header() + webpage(exposure_time, how_many)
        cl.sendall(response.encode('utf-8'))
        cl.close()
        
    
        # NOT SURE HOW THIS WORKS, IF IT IS LOOPING THRU IT AT ALL
        if exposure == False and (counted_exposures < how_many):
            start_time = time()
            print("Started exposure")
            exposure = True
            counted_exposures += 1
            LED.value(not LED.value())
            remote_release()
        
        if exposure == True and ((time() - start_time) >= exposure_time):
            remote_release()
            LED.value(not LED.value())
            print("Ended exposure")
            sleep(sdCard_write_time)        
            exposure = False
            
        if counted_exposures == how_many and exposure == False:
            setting_up = True
            counted_exposures = 0
            print("Reset for next exposure")
    
    except Exception as e:
        print('Error:', e)
        cl.close()
    """
    
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
     """   