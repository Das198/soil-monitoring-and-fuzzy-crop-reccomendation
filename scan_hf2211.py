import socket
import sys

subnet = "10.17.40"
port = 8899

print(f"Scanning {subnet}.0/24 for port {port}...")

for i in range(1, 255):
    ip = f"{subnet}.{i}"
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(0.1)
    
    result = sock.connect_ex((ip, port))
    sock.close()
    
    if result == 0:
        print(f"✓ Port {port} OPEN: {ip}")