from pyModbusTCP.client import ModbusClient
import time
import json
import socket

# --- KONFIGURASI MODBUS ---
SERVER_HOST = "10.10.100.254"  # Ganti dengan IP Address HF2211 Anda
SERVER_PORT = 8899             # Ganti dengan Port TCP HF2211 Anda
SLAVE_IDS = [1, 2, 3]          # Daftar Slave ID yang akan dibaca

# --- KONFIGURASI PEMBACAAN DATA KONTINU ---
REGISTER_START_ADDRESS = 0     
REGISTER_COUNT = 8             # Total 8 register (dari alamat 0 hingga 7)
POLLING_INTERVAL = 1           # Interval total pembacaan dalam detik

# --- PETA NAMA REGISTER ---
# Mapping nama ke indeks (posisi) data dalam array 'registers' yang dibaca (0-7)
REGISTER_MAP = {
    "kelembapan_tanah": 0,    # Registers[0]
    "suhu": 1,                # Registers[1]
    # Register 2 dilewati dari penggunaan, tetapi tetap dibaca oleh Modbus
    "ph_tanah": 3,            # Registers[3]
    "nitrogen": 4,            # Registers[4]
    "fosfor": 5,              # Registers[5]
    "kalium": 6,              # Registers[6]
    "salinity": 7             # Registers[7]
}

# --- PARAMETER YANG MEMBUTUHKAN SCALING 0.1 ---
# Digunakan untuk mengidentifikasi variabel yang harus dibagi 10.0
SCALED_PARAMETERS = ["suhu", "kelembapan_tanah", "ph_tanah"] 

# --- INISIALISASI DAN LOOP UTAMA ---

# Inisialisasi Klien Modbus TCP
client = ModbusClient(
    host=SERVER_HOST, 
    port=SERVER_PORT, 
    auto_open=True, 
    auto_close=False
)

print(f"Mencoba koneksi ke Modbus Gateway {SERVER_HOST}:{SERVER_PORT}...")

try:
    # Buka koneksi awal Modbus
    if client.open():
        print("Koneksi Modbus berhasil dibuka. Memulai pembacaan kontinu...")
    else:
        print("Gagal membuka koneksi Modbus. Periksa gateway.")
        exit()

    # Konfigurasi TCP ke Node-RED
    NODE_RED_IP = "127.0.0.1"   # kalau Node-RED di PC yang sama, pakai localhost
    NODE_RED_PORT = 5020        # port bebas, tapi nanti harus sama di Node-RED

    tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    tcp_socket.connect((NODE_RED_IP, NODE_RED_PORT))
    print(f"Terkoneksi ke Node-RED di {NODE_RED_IP}:{NODE_RED_PORT}")
        
            # --- Loop Pembacaan Kontinu ---
    while True:
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        print(f"\n--- {timestamp} - Mulai Siklus Pembacaan ---")
        
        # Ulangi pembacaan untuk setiap Slave ID
        for unit_id in SLAVE_IDS:
            client.unit_id = unit_id
            
            # Membaca blok 8 register (alamat 0 hingga 7)
            registers = client.read_holding_registers(REGISTER_START_ADDRESS, REGISTER_COUNT)

            if registers:
                mapped_data = {}

                for name, index in REGISTER_MAP.items():
                    raw_value = registers[index]
                    scaled_value = raw_value
                    
                    # Logic scaling
                    if name in SCALED_PARAMETERS:
                        scaled_value = raw_value / 10.0
                    
                    mapped_data[name] = scaled_value

                print(f"[ID {unit_id}] SUKSES:")
                for name, value in mapped_data.items():
                    print(f"  > {name.replace('_', ' ').title()}: {value}")

                # === KIRIM DATA SETIAP SLAVE KE NODE-RED ===
                data = {
                    "slave_id": unit_id,
                    "timestamp": timestamp,
                    "data": mapped_data
                }

                json_data = json.dumps(data) + "\n"
                tcp_socket.sendall(json_data.encode("utf-8"))
                print(f"Data dari ID {unit_id} terkirim ke Node-RED")

            else:
                print(f"[ID {unit_id}] GAGAL membaca register.")
                if not client.is_open:
                    client.open()

            # === DELAY ANTAR SLAVE ===
            time.sleep(0.1)

        # === DELAY ANTAR SIKLUS ===
        time.sleep(2)



except Exception as e:
    print(f"Gagal kirim ke Node-RED: {e}")

except KeyboardInterrupt:
    print("\nProgram dihentikan oleh pengguna (Ctrl+C).")
    
finally:
    # Tutup koneksi Modbus
    if client.is_open:
        client.close()
        print("Koneksi Modbus ditutup.")