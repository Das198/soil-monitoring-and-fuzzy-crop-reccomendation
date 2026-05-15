import socket

# 0.0.0.0 artinya server akan mendengarkan dari IP mana saja (termasuk WiFi lokal)
HOST = '0.0.0.0' 
PORT = 5000

print(f"Memulai Test Server...")
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.bind((HOST, PORT))
    s.listen()
    print(f"Server standby! Menunggu ketukan TCP dari HF2211 di Port {PORT}...")
    
    conn, addr = s.accept()
    with conn:
        print(f"\n[SUKSES] HF2211 Terhubung dari IP: {addr}")
        while True:
            data = conn.recv(1024)
            if not data:
                break
            # Menampilkan data mentah (Hex) karena Modbus RS485 biasanya berupa Hexadecimal
            print(f"Data Mentah (Hex) : {data.hex()}")