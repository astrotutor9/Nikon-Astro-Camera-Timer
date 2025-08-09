import network
import socket
import ure
import utime
from machine import Pin

# Wi-Fi Access Point setup
ssid = 'Camera_Remote'
password = '12345678'

ap = network.WLAN(network.AP_IF)
ap.config(essid=ssid, password=password)
ap.active(True)

# Relay (camera trigger) setup
FOCUS_RELAY = Pin(15, Pin.OUT)
SHUTTER_RELAY = Pin(14, Pin.OUT)
redLED = Pin(13, Pin.OUT)
greenLED = Pin(12, Pin.OUT)
redLED.value(0)

# Simple LED to inform unit powered up
greenLED.value(1)

FOCUS_RELAY.value(1)
SHUTTER_RELAY.value(1)

# Camera control function
def remote_release():
    FOCUS_RELAY.value(0)
    SHUTTER_RELAY.value(0)
    utime.sleep_ms(200)
    SHUTTER_RELAY.value(1)
    FOCUS_RELAY.value(1)

sd_card_write_time = 1000  # milliseconds between exposures

# HTTP response header
def response_header():
    return 'HTTP/1.0 200 OK\r\nContent-type: text/html\r\n\r\n'

# HTML webpage
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

# HTTP server setup
addr = socket.getaddrinfo('0.0.0.0', 80)[0][-1]
s = socket.socket()
s.bind(addr)
s.listen(1)

print('Server running at:', ap.ifconfig()[0])

# Initialize variables
exposure_time, how_many = 5, 5

# Main loop
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
                print('Starting: exposure_time={}, how_many={}'.format(exposure_time, how_many))

                for count in range(how_many):
                    redLED.value(1)
                    remote_release()
                    start = utime.ticks_ms()

                    while utime.ticks_diff(utime.ticks_ms(), start) < (exposure_time * 1000):
                        #redLED.value(1)
                        pass

                    remote_release()
                    redLED.value(0)
                    print('Exposure {} complete.'.format(count + 1))

                    if count < how_many - 1:
                        utime.sleep_ms(sd_card_write_time)

        response = response_header() + webpage(exposure_time, how_many)
        cl.sendall(response.encode('utf-8'))
        cl.close()

    except Exception as e:
        print('Error:', e)
        cl.close()
