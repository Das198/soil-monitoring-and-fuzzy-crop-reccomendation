from pyModbusTCP.client import ModbusClient
import time
from typing import Dict, Any

# --- KONFIGURASI MODBUS ---
SERVER_HOST = "10.10.100.254"
SERVER_PORT = 8899
SLAVE_IDS = [1, 2, 3]

# --- KONFIGURASI PEMBACAAN DATA KONTINU ---
REGISTER_START_ADDRESS = 0     
REGISTER_COUNT = 8             
POLLING_INTERVAL = 1           

# --- PETA NAMA REGISTER & SKALA ---
REGISTER_MAP = {
    "kelembapan_tanah": 0,
    "suhu": 1,
    "ph_tanah": 3,
    "nitrogen": 4,
    "fosfor": 5,
    "kalium": 6,
    "salinity": 7
}

# Parameter yang membutuhkan pembagian 10.0 (resolusi 0.1)
SCALED_PARAMETERS = ["suhu", "kelembapan_tanah", "ph_tanah"] 

# --- AMBANG BATAS KESEHATAN TANAH (Dapat Disesuaikan) ---
# Format: { 'nama_parameter': (MIN_IDEAL, MAX_IDEAL) }
HEALTH_LIMITS: Dict[str, tuple[float, float]] = {
    "kelembapan_tanah": (30.0, 60.0), # Ideal 30% - 60%
    "suhu": (20.0, 35.0),             # Ideal 20°C - 35°C
    "ph_tanah": (5.5, 7.0),           # Ideal pH 5.5 - 7.0 (Netral ke agak asam)
    "nitrogen": (50, 100),            # Nilai contoh mg/kg
    "fosfor": (15, 40),               # Nilai contoh mg/kg
    "kalium": (100, 200),             # Nilai contoh mg/kg
    "salinity": (0.0, 2.0)            # Ideal Salinitas < 2 dS/m
}

# --- FUNGSI ANALISIS KESEHATAN ---
def get_health_status(data: Dict[str, Any]) -> tuple[str, str]:
    """Menentukan status kesehatan berdasarkan ambang batas."""
    
    overall_status = "SEHAT"
    issues = []
    
    for name, value in data.items():
        if name in HEALTH_LIMITS:
            min_ideal, max_ideal = HEALTH_LIMITS[name]
            
            if value < min_ideal:
                issues.append(f"{name.replace('_', ' ').title()} ({value}) terlalu RENDAH (Min: {min_ideal})")
                overall_status = "PERLU PERHATIAN"
            elif value > max_ideal:
                issues.append(f"{name.replace('_', ' ').title()} ({value}) terlalu TINGGI (Max: {max_ideal})")
                overall_status = "PERLU PERHATIAN"
            
    # Jika ada masalah, status bisa jadi Kritis jika terdapat banyak masalah, 
    # atau status yang paling serius
    if len(issues) >= 3:
         overall_status = "KRITIS"
    elif len(issues) > 0 and overall_status != "KRITIS":
         overall_status = "PERLU PERHATIAN"
    
    return overall_status, "\n  - ".join(issues)

# --- INISIALISASI DAN LOOP UTAMA ---

client = ModbusClient(
    host=SERVER_HOST, 
    port=SERVER_PORT, 
    auto_open=True, 
    auto_close=False
)

print(f"Mencoba koneksi ke Modbus Gateway {SERVER_HOST}:{SERVER_PORT}...")

try:
    if client.open():
        print("Koneksi Modbus berhasil dibuka. Memulai monitoring kesehatan tanah...")
    else:
        print("Gagal membuka koneksi Modbus. Periksa gateway.")
        exit()
        
    while True:
        timestamp_cycle = time.strftime("%Y-%m-%d %H:%M:%S")
        print(f"\n--- {timestamp_cycle} - MONITORING KESEHATAN TANAH ---")
        
        for unit_id in SLAVE_IDS:
            client.unit_id = unit_id
            registers = client.read_holding_registers(REGISTER_START_ADDRESS, REGISTER_COUNT)

            if registers:
                # 1. PETAKAN DAN SKALAKAN DATA
                mapped_data: Dict[str, float | int] = {}
                for name, index in REGISTER_MAP.items():
                    raw_value = registers[index]
                    scaled_value: float | int = raw_value
                    
                    if name in SCALED_PARAMETERS:
                        scaled_value = raw_value / 10.0 
                    
                    mapped_data[name] = scaled_value

                # 2. ANALISIS KESEHATAN
                status, issues_detail = get_health_status(mapped_data)
                
                # 3. CETAK HASIL
                print(f"[{status}] Data Slave ID {unit_id} (Sensor {unit_id}):")
                
                # Cetak semua nilai parameter
                for name, value in mapped_data.items():
                    display_name = name.replace('_', ' ').title()
                    # Tentukan format tampilan desimal
                    format_str = f":.1f" if name in SCALED_PARAMETERS else f""
                    print(f"  > {display_name}: {{value{format_str}}}".format(value=value))

                # Cetak detail masalah
                if issues_detail:
                    print(f"  [MASALAH TERDETEKSI]:\n  - {issues_detail}")
                
            else:
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