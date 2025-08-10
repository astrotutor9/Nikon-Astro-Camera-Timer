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
FOCUS_RELAY = Pin(13, Pin.OUT)
SHUTTER_RELAY = Pin(12, Pin.OUT)
redLED = Pin(15, Pin.OUT)
greenLED = Pin(14, Pin.OUT)
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


try:
    import _thread
    threading_supported = True
except:
    threading_supported = False

cancel_requested = False
exposure_thread_running = False
current_params = {'exposure_time': 5, 'how_many': 5}
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
  form {{ display: flex; flex-direction: column; align-items: center; gap: 16px; }}
  .arrow {{ font-size: 80px; cursor: pointer; user-select: none; line-height: 1; }}
  .value {{ font-size: 50px; }}
  button {{ font-size: 30px; margin-top: 0; color: black; background-color: red; border: none; padding: 8px 20px; cursor: pointer; }}
  p {{ font-size: 40px; margin: 0; }}
  /* Layout */
  .controls {{ display: grid; grid-template-columns: 1fr 1fr; column-gap: 48px; align-items: start; justify-items: center; margin-top: 10px; }}
  .control {{ display: flex; flex-direction: column; align-items: center; gap: 6px; justify-content: center; }}
  .labels {{ display: grid; grid-template-columns: 1fr 1fr; column-gap: 48px; justify-items: center; margin-bottom: 10px; margin-top: 20px; }}
  .top-actions {{ width: 100%; display: flex; justify-content: center; margin-bottom: 30px; }}
  .bottom-actions {{ width: 100%; display: flex; justify-content: center; margin-top: 40px; }}
</style>
</head>
<body>
<form method='POST'>
  <!-- Top action -->
  <div class='top-actions'>
    <button type='submit' name='action' value='cancel'>Cancel</button>
  </div>

  <!-- Labels row above arrows -->
  <div class='labels'>
    <p>Time</p>
    <p>Number</p>
  </div>

  <!-- Two side-by-side selectors -->
  <div class='controls'>
    <!-- Exposure time column -->
    <div class='control'>
      <span class='arrow' onclick='update("time", 1)'>&#9650;</span>
      <div class='value' id='time'>{exposure_time}</div>
      <span class='arrow' onclick='update("time", -1)'>&#9660;</span>
      <input type='hidden' name='exposure_time' id='time_input' value='{exposure_time}'/>
    </div>

    <!-- Number of exposures column -->
    <div class='control'>
      <span class='arrow' onclick='update("number", 1)'>&#9650;</span>
      <div class='value' id='number'>{how_many}</div>
      <span class='arrow' onclick='update("number", -1)'>&#9660;</span>
      <input type='hidden' name='how_many' id='number_input' value='{how_many}'/>
    </div>
  </div>

  <!-- Bottom action -->
  <div class='bottom-actions'>
    <button type='submit'>Submit</button>
  </div>
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


def exposures_worker(exposure_time, how_many):
    global cancel_requested, exposure_thread_running
    exposure_thread_running = True
    try:
        for count in range(how_many):
            if cancel_requested:
                break
            redLED.value(1)
            # Start exposure (edge)
            remote_release()
            start = utime.ticks_ms()
            # Run exposure, allow cancellation
            while utime.ticks_diff(utime.ticks_ms(), start) < (exposure_time * 1000):
                if cancel_requested:
                    break
                pass
            # Stop exposure (edge)
            remote_release()
            redLED.value(0)
            if cancel_requested:
                break
            if count < how_many - 1:
                utime.sleep_ms(sd_card_write_time)
    finally:
        exposure_thread_running = False
        cancel_requested = False

while True:
    try:
        cl, addr = s.accept()
        request = cl.recv(1024).decode('utf-8')

        if 'POST' in request:
            # Look for cancel first
            action_match = ure.search(r"action=([A-Za-z]+)", request)
            if action_match and action_match.group(1) == 'cancel':
                # Set cancel flag and release once immediately
                try:
                    cancel_requested = True
                except NameError:
                    pass
                remote_release()
                print('Cancel requested: issued remote_release and set cancel flag.')
            else:
                exposure_match = ure.search(r"exposure_time=(\d+)", request)
                number_match = ure.search(r"how_many=(\d+)", request)

                if exposure_match and number_match:
                    exposure_time = int(exposure_match.group(1))
                    how_many = int(number_match.group(1))
                    current_params['exposure_time'] = exposure_time
                    current_params['how_many'] = how_many
                    print('Starting: exposure_time={}, how_many={}'.format(exposure_time, how_many))

                    # Run exposures in background when possible so Cancel can be processed
                    if 'threading_supported' in globals() and threading_supported:
                        try:
                            _thread.start_new_thread(exposures_worker, (exposure_time, how_many))
                        except Exception as e:
                            print('Thread start failed, running inline:', e)
                            exposures_worker(exposure_time, how_many)
                    else:
                        exposures_worker(exposure_time, how_many)
        response = response_header() + webpage(current_params.get('exposure_time', 5), current_params.get('how_many', 5))
        cl.sendall(response.encode('utf-8'))
        cl.close()

    except Exception as e:
        print('Error:', e)
        cl.close()
