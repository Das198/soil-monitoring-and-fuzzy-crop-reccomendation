import socket
import concurrent.futures
import ipaddress

def check_port(ip):
    port = 8899
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(0.2)
    result = sock.connect_ex((str(ip), port))
    sock.close()
    if result == 0:
        return str(ip)
    return None

if __name__ == "__main__":
    print("Scanning 10.17.40.0/22 for port 8899...")
    network = ipaddress.ip_network('10.17.40.0/22')

    found = False
    with concurrent.futures.ThreadPoolExecutor(max_workers=200) as executor:
        futures = [executor.submit(check_port, ip) for ip in network.hosts()]
        for future in concurrent.futures.as_completed(futures):
            res = future.result()
            if res:
                print(f"[OPEN] Port 8899 OPEN: {res}")
                found = True
                
    if not found:
        print("No devices found with port 8899 open on the subnet.")
    print("Scan complete.")
