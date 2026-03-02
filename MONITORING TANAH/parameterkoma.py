from pyModbusTCP.client import ModbusClient
import time

# --- KONFIGURASI MODBUS ---
SERVER_HOST = "10.10.100.254"  # Ganti dengan IP Address HF2211 Anda
SERVER_PORT = 8899             # Ganti dengan Port TCP HF2211 Anda
SLAVE_IDS = [1]          # Daftar Slave ID yang akan dibaca

# --- KONFIGURASI PEMBACAAN DATA KONTINU ---
REGISTER_START_ADDRESS = 0     
REGISTER_COUNT = 8             # Total 8 register (dari alamat 0 hingga 7)
POLLING_INTERVAL = 1           # Interval total pembacaan dalam detik

# --- PETA NAMA REGISTER ---
REGISTER_MAP = {
    "kelembapan_tanah": 0,
    "suhu": 1,
    "konduktivitas": 2,
    "ph_tanah": 3,  # Indeks 3
    "nitrogen": 4,
    "fosfor": 5,
    "kalium": 6,
    "salinity": 7
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
    if client.open():
        print("Koneksi Modbus berhasil dibuka. Memulai pembacaan kontinu...")
        print(f"Catatan: Resolusi 0.1 diterapkan pada: {', '.join(SCALED_PARAMETERS).title()}.")
    else:
        print("Gagal membuka koneksi Modbus. Periksa gateway.")
        exit()
        
    # --- Loop Pembacaan Kontinu ---
    while True:
        timestamp_cycle = time.strftime("%Y-%m-%d %H:%M:%S")
        print(f"\n--- {timestamp_cycle} - Mulai Siklus Pembacaan ---")
        
        for unit_id in SLAVE_IDS:
            client.unit_id = unit_id
            
            registers = client.read_holding_registers(REGISTER_START_ADDRESS, REGISTER_COUNT)

            if registers:
                # Pembacaan berhasil: PETAKAN DATA KE NAMA DAN SKALAKAN
                mapped_data = {}
                
                for name, index in REGISTER_MAP.items():
                    raw_value = registers[index]
                    scaled_value = raw_value
                    
                    # Logika Skala (Scaling Logic)
                    if name in SCALED_PARAMETERS:
                        # Bagi dengan 10.0 untuk mendapatkan resolusi 0.1
                        scaled_value = raw_value / 10.0 
                    
                    mapped_data[name] = scaled_value
                
                # Cetak hasilnya ke konsol
                print(f"[ID {unit_id}] SUKSES:")
                for name, value in mapped_data.items():
                    # Gunakan format .1f untuk menampilkan satu angka di belakang koma 
                    if name in SCALED_PARAMETERS:
                        print(f"  > {name.replace('_', ' ').title()}: {value:.1f}")
                    else:
                        print(f"  > {name.replace('_', ' ').title()}: {value}")
                
            else:
                # Gagal membaca
                print(f"[ID {unit_id}] GAGAL membaca register (Timeout/Koneksi Serial).")
                if not client.is_open:
                     client.open()

        time.sleep(POLLING_INTERVAL)

except KeyboardInterrupt:
    print("\nProgram dihentikan oleh pengguna (Ctrl+C).")
except Exception as e:
    print(f"\nTerjadi kesalahan tak terduga: {e}")
    
finally:
    if client.is_open:
        client.close()
        print("Koneksi Modbus ditutup.")