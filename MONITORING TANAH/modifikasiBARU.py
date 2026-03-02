from pyModbusTCP.client import ModbusClient
import time
import json
import socket
from typing import Dict, Any, List, Tuple

# --- KONFIGURASI MODBUS ---
SERVER_HOST = "10.10.100.254"  # Ganti dengan IP Address HF2211 Anda
SERVER_PORT = 8899             # Ganti dengan Port TCP HF2211 Anda
SLAVE_IDS: List[int] = [1, 2, 3]  # Daftar Slave ID yang akan dibaca

# --- KONFIGURASI PEMBACAAN DATA KONTINU ---
REGISTER_START_ADDRESS = 0     
REGISTER_COUNT = 8             # Total 8 register (dari alamat 0 hingga 7)
POLLING_INTERVAL = 2           # Interval total pembacaan antar siklus dalam detik (diubah dari 1 ke 2)
SLAVE_DELAY: float = 0.1       # Jeda antar pembacaan slave (detik)

# --- KONFIGURASI NODE-RED (TCP SOCKET) ---
NODE_RED_IP: str = "127.0.0.1"   # kalau Node-RED di PC yang sama, pakai localhost
NODE_RED_PORT: int = 5020        # port bebas, tapi nanti harus sama di Node-RED

# --- PETA NAMA REGISTER ---
# Mapping nama ke indeks (posisi) data dalam array 'registers' yang dibaca (0-7)
REGISTER_MAP: Dict[str, int] = {
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
SCALED_PARAMETERS: List[str] = ["suhu", "kelembapan_tanah", "ph_tanah"] 

# --- AMBANG BATAS KESEHATAN TANAH (Diambil dari aturparameter.py) ---
# Format: { 'nama_parameter': (MIN_IDEAL, MAX_IDEAL) }
HEALTH_LIMITS: Dict[str, Tuple[float, float]] = {
    "kelembapan_tanah": (30.0, 60.0), # Ideal 30% - 60%
    "suhu": (20.0, 35.0),             # Ideal 20°C - 35°C
    "ph_tanah": (5.5, 7.0),           # Ideal pH 5.5 - 7.0
    "nitrogen": (50.0, 100.0),        # Nilai contoh mg/kg
    "fosfor": (15.0, 40.0),           # Nilai contoh mg/kg
    "kalium": (100.0, 200.0),         # Nilai contoh mg/kg
    "salinity": (0.0, 2.0)            # Ideal Salinitas < 2 dS/m
}

# --- FUNGSI ANALISIS KESEHATAN (Diambil dari aturparameter.py) ---
def get_health_status(data: Dict[str, float | int]) -> Tuple[str, str]:
    """Menentukan status kesehatan berdasarkan ambang batas."""
    
    overall_status = "SEHAT"
    issues = []
    
    for name, value in data.items():
        if name in HEALTH_LIMITS:
            min_ideal, max_ideal = HEALTH_LIMITS[name]
            
            # Konversi ke float untuk perbandingan akurat
            val_float = float(value)
            
            if val_float < min_ideal:
                issues.append(f"{name.replace('_', ' ').title()} ({value}) terlalu RENDAH (Min: {min_ideal})")
                overall_status = "PERLU PERHATIAN"
            elif val_float > max_ideal:
                issues.append(f"{name.replace('_', ' ').title()} ({value}) terlalu TINGGI (Max: {max_ideal})")
                overall_status = "PERLU PERHATIAN"
            
    # Logika peningkatan status
    if len(issues) >= 3:
         overall_status = "KRITIS"
    elif len(issues) > 0 and overall_status != "KRITIS":
         overall_status = "PERLU PERHATIAN"
    
    return overall_status, "\n  - ".join(issues)

# --- INISIALISASI DAN LOOP UTAMA ---

# Inisialisasi Klien Modbus TCP
client = ModbusClient(
    host=SERVER_HOST, 
    port=SERVER_PORT, 
    auto_open=True, 
    auto_close=False
)

# Inisialisasi Socket TCP untuk Node-RED
tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

print(f"Mencoba koneksi ke Modbus Gateway {SERVER_HOST}:{SERVER_PORT}...")

try:
    # Buka koneksi awal Modbus
    if client.open():
        print("Koneksi Modbus berhasil dibuka.")
    else:
        print("Gagal membuka koneksi Modbus. Periksa gateway.")
        exit()

    # Hubungkan ke Node-RED
    tcp_socket.connect((NODE_RED_IP, NODE_RED_PORT))
    print(f"Terkoneksi ke Node-RED di {NODE_RED_IP}:{NODE_RED_PORT}. Memulai pembacaan kontinu...")
        
    # --- Loop Pembacaan Kontinu ---
    while True:
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        print(f"\n--- {timestamp} - Mulai Siklus Pembacaan & Analisis ---")
        
        # Ulangi pembacaan untuk setiap Slave ID
        for unit_id in SLAVE_IDS:
            client.unit_id = unit_id
            
            # Membaca blok 8 register
            registers = client.read_holding_registers(REGISTER_START_ADDRESS, REGISTER_COUNT)

            if registers:
                # 1. PETAKAN DAN SKALAKAN DATA
                mapped_data: Dict[str, float | int] = {}
                for name, index in REGISTER_MAP.items():
                    raw_value = registers[index]
                    scaled_value: float | int = raw_value
                    
                    # Logic scaling
                    if name in SCALED_PARAMETERS:
                        scaled_value = raw_value / 10.0
                    
                    mapped_data[name] = scaled_value

                # 2. ANALISIS KESEHATAN
                status, issues_detail = get_health_status(mapped_data)

                # 3. CETAK HASIL DI KONSOL
                print(f"[{status}] Data Slave ID {unit_id} (Sensor {unit_id}):")
                
                for name, value in mapped_data.items():
                    display_name = name.replace('_', ' ').title()
                    # Tentukan format tampilan desimal
                    format_str = f":.1f" if name in SCALED_PARAMETERS else f""
                    print(f"  > {display_name}: {{value{format_str}}}".format(value=value))
                
                if issues_detail:
                    print(f"  [MASALAH TERDETEKSI]:\n  - {issues_detail}")


                # 4. KIRIM DATA SETIAP SLAVE KE NODE-RED
                data_to_send = {
                    "slave_id": unit_id,
                    "timestamp": timestamp,
                    "status": status, # Tambahkan status kesehatan
                    "issues": issues_detail.replace('\n  - ', ' | ') if issues_detail else "OK", # Tambahkan detail isu
                    "data": mapped_data
                }

                json_data = json.dumps(data_to_send) + "\n"
                tcp_socket.sendall(json_data.encode("utf-8"))
                print(f"  [Node-RED] Data dari ID {unit_id} terkirim.")

            else:
                print(f"[ID {unit_id}] GAGAL membaca register (Timeout/Koneksi Serial).")
                if not client.is_open:
                    client.open()

            # === DELAY ANTAR SLAVE ===
            time.sleep(SLAVE_DELAY)

        # === DELAY ANTAR SIKLUS ===
        time.sleep(POLLING_INTERVAL)


except ConnectionRefusedError:
     print(f"\nGagal koneksi ke Node-RED di {NODE_RED_IP}:{NODE_RED_PORT}. Pastikan Node-RED berjalan dan node TCP aktif.")
except KeyboardInterrupt:
    print("\nProgram dihentikan oleh pengguna (Ctrl+C).")
    
except Exception as e:
    print(f"\nTerjadi kesalahan tak terduga: {e}")

finally:
    # Tutup koneksi Modbus
    if client.is_open:
        client.close()
        print("Koneksi Modbus ditutup.")
    # Tutup koneksi TCP Node-RED
    if tcp_socket:
        tcp_socket.close()
        print("Koneksi TCP Node-RED ditutup.")