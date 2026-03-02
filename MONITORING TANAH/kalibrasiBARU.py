from pyModbusTCP.client import ModbusClient
import time
from typing import List

# --- KONFIGURASI MODBUS ---
SERVER_HOST = "10.10.100.254" 
SERVER_PORT = 8899 
SLAVE_IDS: List[int] = [1, 2, 3] 

# --- KONFIGURASI REGISTER (TERKONFIRMASI DARI MANUAL) ---
PH_CALIBRATION_REGISTER: int = 83 # 0x0053: PH offset (Digunakan untuk semua penulisan)
PH_BASE_VALUE: int = 7
           # Nilai pH 9.18 diskalakan (Percobaan A)
PH_BASE_COMMAND: int = 1          # Perintah alternatif (Percobaan B)

# --- INISIALISASI KLIEN MODBUS ---
client = ModbusClient(
    host=SERVER_HOST, 
    port=SERVER_PORT, 
    auto_open=True, 
    auto_close=False,
    timeout=5.0 
)

def calibrate_ph_base_step(unit_id: int, scaled_value: int, step_name: str) -> bool:
    """Melakukan penulisan kalibrasi pH basa ke register 0x0053 (83)."""
    client.unit_id = unit_id
    
    print(f"  - Mencoba menulis {step_name} ({scaled_value}) ke Reg {PH_CALIBRATION_REGISTER}...")
    
    is_ok = client.write_single_register(PH_CALIBRATION_REGISTER, scaled_value)

    if is_ok:
        time.sleep(5.0) # Jeda waktu untuk sensor memproses
        return True
    else:
        print(f"  - [GAGAL] Gagal menulis nilai ke Reg {PH_CALIBRATION_REGISTER}.")
        return False

def read_ph_value(unit_id: int) -> float | None:
    """Membaca nilai pH terkalibrasi dari register 3 (0x0003)."""
    client.unit_id = unit_id
    registers = client.read_holding_registers(3, 1) 
    if registers and len(registers) > 0:
        return registers[0] / 10.0
    return None

# --- PROGRAM UTAMA KALIBRASI BASA (LANGKAH 3) ---
print(f"==================================================")
print(f"  MODBUS PH CALIBRATION (Fokus Titik 9.18 - Reg 83)")
print(f"==================================================")
print("ASUMSI: Titik pH 6.86 dan 4.01 SUDAH berhasil dilakukan sebelumnya.")

try: 
    if not client.open():
        print("Gagal membuka koneksi Modbus.")
        exit()
    print("Koneksi Modbus berhasil dibuka.\n")

    for unit_id in SLAVE_IDS:
        print(f"███ FOKUS KALIBRASI BASA (pH 9.18) ID {unit_id} ███")
        
        print(f"\n[STEP] SILAKAN CELUPKAN SENSOR ID {unit_id} KE LARUTAN BUFFER pH 9.18!")
        input("   >>> Tekan ENTER setelah pembacaan sensor stabil...")
        
        # PERCOBAAN A: Tulis nilai 92 ke register 83
        print("\n--- PERCOBAAN A: Tulis Nilai pH Target (92) ---")
        if calibrate_ph_base_step(unit_id, PH_BASE_VALUE, "Nilai Target 92"):
            current_ph = read_ph_value(unit_id)
            if 9.0 < current_ph < 9.5:
                print(f"   [SUKSES] Kalibrasi basa berhasil! PH TERKALIBRASI: {current_ph:.3f}")
                continue # Lanjut ke slave ID berikutnya

        # PERCOBAAN B: Tulis nilai perintah 1 ke register 83 (Jika A Gagal)
        print("\n--- PERCOBAAN B: Tulis Perintah Khusus (1) ---")
        if calibrate_ph_base_step(unit_id, PH_BASE_COMMAND, f"Perintah {PH_BASE_COMMAND}"):
            current_ph = read_ph_value(unit_id)
            if 9.0 < current_ph < 9.5:
                print(f"   [SUKSES] Kalibrasi basa berhasil dengan perintah 1! PH TERKALIBRASI: {current_ph:.3f}")
            else:
                print(f"   [HASIL] Perintah 1 dijalankan, PH saat ini: {current_ph:.3f}")

        print(f"\nKALIBRASI ID {unit_id} SELESAI. Silakan bilas sensor.")
        print("-" * 40)

except KeyboardInterrupt: 
    print("\nProgram dihentikan oleh pengguna (Ctrl+C).")
except Exception as e: 
    print(f"\nTerjadi kesalahan tak terduga: {e}")
    
finally: 
    if client.is_open:
        client.close()
        print("Koneksi Modbus ditutup.") 