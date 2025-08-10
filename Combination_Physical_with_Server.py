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
current_exposure_num = 0   # 0 when idle, otherwise 1..how_many

# HTTP response header
def response_header():
    return 'HTTP/1.0 200 OK\r\nContent-type: text/html\r\n\r\n'

def response_header_text():
    return 'HTTP/1.0 200 OK\r\nContent-type: text/plain\r\nCache-Control: no-store\r\n\r\n'

def redirect_see_other(client):
    # PRG: avoid form resubmission and "page isn't working" after POST
    try:
        client.sendall(b"HTTP/1.0 303 See Other\r\nLocation: /\r\nCache-Control: no-store\r\n\r\n")
    except Exception as e:
        print("Redirect send failed:", e)

# HTML webpage
def webpage(exposure_time=5, how_many=5, exp_num=0):
    html = f"""
<!DOCTYPE html>
<html lang='en'>
<head>
<meta charset='UTF-8'>
<meta name='viewport' content='width=device-width, initial-scale=1.0'>
<title>Pico Control</title>
<style>
  body {{ background-color: black; color: red; text-align: center; font-family: Arial, Helvetica, sans-serif; padding-top: 20px; }}
  form {{ display: flex; flex-direction: column; align-items: center; gap: 16px; }}
  .arrow {{ font-size: 80px; cursor: pointer; user-select: none; line-height: 1; }}
  .value {{ font-size: 50px; }}
  button {{ font-size: 30px; margin-top: 0; color: black; background-color: red; border: none; padding: 8px 20px; cursor: pointer; }}
  p {{ font-size: 40px; margin: 0; }}
  /* Layout */
  .controls {{ display: grid; grid-template-columns: 1fr 1fr; column-gap: 48px; align-items: center; justify-items: center; }}
  .control {{ display: flex; flex-direction: column; align-items: center; gap: 6px; }}
  /* Ensure labels are in same columns as controls */
  .labels {{ display: grid; grid-template-columns: 1fr 1fr; column-gap: 48px; justify-items: center; }}
  /* Spacing helpers so Cancel is at top and Submit at bottom */
  .top-actions, .bottom-actions {{ width: 100%; display: flex; justify-content: center; }}
  .top-actions {{ margin-bottom: 30px; }}
  .labels {{ margin-bottom: 10px; margin-top: 20px; }}
  .bottom-actions {{ margin-top: 40px; }}
  .status {{ margin-top: 16px; font-size: 28px; }}
</style>
</head>
<body>
<form method='POST' onsubmit='startPolling()'>
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

  <div class='status'>Exp Number: <span id='expnum'>{exp_num}</span></div>
</form>

<script>
// Fixed time steps for exposure_time
const TIME_STEPS = [5, 10, 15, 20, 25, 30, 45, 60, 90, 120, 180, 240, 360, 480];

function stepTime(current, delta) {{
  // Find index of current, default to the nearest lower step if not found
  let idx = TIME_STEPS.indexOf(current);
  if (idx === -1) {{
    idx = 0;
    for (let i = 0; i < TIME_STEPS.length; i++) {{
      if (TIME_STEPS[i] <= current) idx = i;
      else break;
    }}
  }}
  idx = Math.max(0, Math.min(TIME_STEPS.length - 1, idx + delta));
  return TIME_STEPS[idx];
}}

function update(id, change) {{
  // Number still increments by 1 within limits. Time uses the fixed steps list.
  const limits = {{'number': [1, 100]}};
  let valElement = document.getElementById(id);
  let inputElement = document.getElementById(id + '_input');
  let val = parseInt(valElement.textContent);
  if (id === 'time') {{
    val = stepTime(val, change);
  }} else {{
    if (isNaN(val)) val = limits[id][0];
    val = Math.min(limits[id][1], Math.max(limits[id][0], val + change));
  }}
  valElement.textContent = val;
  inputElement.value = val;
}}

// Controlled polling that auto-stops at zero
let pollTimer = null;

function startPolling() {{
  if (!pollTimer) {{
    pollTimer = setInterval(pollExpNum, 500);
  }}
}}

function stopPolling() {{
  if (pollTimer) {{
    clearInterval(pollTimer);
    pollTimer = null;
  }}
}}

function pollExpNum() {{
  try {{
    fetch('/status', {{ cache: 'no-store' }})
      .then(r => r.text())
      .then(txt => {{
        const n = parseInt(txt);
        if (!Number.isNaN(n)) {{
          document.getElementById('expnum').textContent = n;
          if (n === 0) {{
            stopPolling();
          }} else {{
            // ensure polling stays on while run is active
            startPolling();
          }}
        }}
      }})
      .catch(() => {{}});
  }} catch (e) {{}}
}}

// Start polling if the initial number isn't zero (e.g. page loaded mid-run)
document.addEventListener('DOMContentLoaded', () => {{
  const initial = parseInt(document.getElementById('expnum').textContent);
  if (!Number.isNaN(initial) && initial !== 0) {{
    startPolling();
  }}
}});
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

def exposures_worker(exposure_time, how_many):
    global cancel_requested, exposure_thread_running, current_exposure_num
    exposure_thread_running = True
    current_exposure_num = 0
    try:
        for count in range(how_many):
            if cancel_requested:
                break
            current_exposure_num = count + 1  # 1-based for display
            redLED.value(1)
            # Start exposure (edge)
            remote_release()
            start = utime.ticks_ms()
            # Run exposure, allow cancellation
            while utime.ticks_diff(utime.ticks_ms(), start) < (exposure_time * 1000):
                if cancel_requested:
                    break
            # Stop exposure (edge)
            remote_release()
            redLED.value(0)
            if cancel_requested:
                break
            if count < how_many - 1:
                utime.sleep_ms(sd_card_write_time)
    finally:
        exposure_thread_running = False
        current_exposure_num = 0
        cancel_requested = False

while True:
    try:
        cl, addr = s.accept()
        request = cl.recv(1024).decode('utf-8')
        is_post = 'POST' in request

        # Very small/naive request line parse
        first_line = request.split('\r\n', 1)[0]
        path = '/'
        if first_line.startswith('GET'):
            parts = first_line.split(' ')
            if len(parts) >= 2:
                path = parts[1]

        # Status endpoint for polling
        if path.startswith('/status'):
            resp = response_header_text() + str(current_exposure_num)
            cl.sendall(resp.encode('utf-8'))
            cl.close()
            continue

        if is_post:
            # Cancel first
            action_match = ure.search(r"action=([A-Za-z]+)", request)
            if action_match and action_match.group(1) == 'cancel':
                cancel_requested = True
                remote_release()  # one immediate release
                print('Cancel requested: issued remote_release and set cancel flag.')
                redirect_see_other(cl)
                cl.close()
                continue

            # Otherwise, parse parameters and start a run
            exposure_match = ure.search(r"exposure_time=(\d+)", request)
            number_match = ure.search(r"how_many=(\d+)", request)
            if exposure_match and number_match:
                exposure_time = int(exposure_match.group(1))
                how_many = int(number_match.group(1))
                # Snap exposure_time to the nearest allowed step on the server as well
                STEPS = [5, 10, 15, 20, 25, 30, 45, 60, 90, 120, 180, 240, 360, 480]
                exposure_time = max(min(exposure_time, STEPS[-1]), STEPS[0])
                # Find nearest step not exceeding the value
                snapped = STEPS[0]
                for v in STEPS:
                    if v <= exposure_time:
                        snapped = v
                exposure_time = snapped
                current_params['exposure_time'] = exposure_time
                current_params['how_many'] = how_many
                print('Starting: exposure_time={}, how_many={}'.format(exposure_time, how_many))
                if threading_supported:
                    try:
                        _thread.start_new_thread(exposures_worker, (exposure_time, how_many))
                    except Exception as e:
                        print('Thread start failed, running inline:', e)
                        exposures_worker(exposure_time, how_many)
                else:
                    exposures_worker(exposure_time, how_many)
                # Redirect after submit too
                redirect_see_other(cl)
                cl.close()
                continue

        # Normal GET (or POST without recognised fields): render page
        response = response_header() + webpage(current_params.get('exposure_time', 5),
                                               current_params.get('how_many', 5),
                                               current_exposure_num)
        cl.sendall(response.encode('utf-8'))
        cl.close()

    except Exception as e:
        print('Error:', e)
        try:
            cl.close()
        except:
            pass
