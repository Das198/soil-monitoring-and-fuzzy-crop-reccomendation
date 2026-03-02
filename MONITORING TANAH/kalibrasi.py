from pyModbusTCP.client import ModbusClient
import time
from typing import Dict, List, Tuple

# --- KONFIGURASI MODBUS ---
SERVER_HOST = "10.10.100.254" 
SERVER_PORT = 8899 
SLAVE_IDS: List[int] = [1] 

# --- KONFIGURASI KALIBRASI PH CWT-SOIL ---
CALIBRATION_VALUE_REGISTER: int = 83  # 0x0053
CALIBRATION_COMMAND_REGISTER: int = 84 # 0x0054 (Dugaan untuk Perintah SIMPAN/KELUAR)
COMMAND_SAVE_VALUE: int = 0          # Nilai umum untuk perintah 'SIMPAN' atau 'KELUAR'

# HANYA SATU TITIK NETRAL
CALIBRATION_POINT: Dict[str, int] = {
    "6.86 (Titik Netral)": 7 
}

# --- INISIALISASI KLIEN MODBUS ---
client = ModbusClient(
    host=SERVER_HOST, 
    port=SERVER_PORT, 
    auto_open=True, 
    auto_close=False,
    timeout=5.0 
)

def write_calibration_point_and_save(unit_id: int, buffer_name: str, scaled_value: int) -> bool:
    """Melakukan operasi Modbus dua langkah: Tulis Nilai Target, lalu Tulis Perintah Simpan (0)."""
    client.unit_id = unit_id
    
    # 1. TULIS NILAI pH TARGET (Reg 0x0053 / 83)
    print(f"  - 1. Tulis Nilai pH Target ({buffer_name}) ke Reg {CALIBRATION_VALUE_REGISTER}...")
    value_ok = client.write_single_register(CALIBRATION_VALUE_REGISTER, scaled_value)

    if not value_ok:
        print(f"  - [GAGAL] Menulis nilai ke Reg {CALIBRATION_VALUE_REGISTER}.")
        return False

    # 2. TULIS PERINTAH SIMPAN & KELUAR (Reg 0x0054 / 84)
    print(f"  - 2. Tulis Perintah SIMPAN ({COMMAND_SAVE_VALUE}) ke Reg {CALIBRATION_COMMAND_REGISTER}...")
    command_ok = client.write_single_register(CALIBRATION_COMMAND_REGISTER, COMMAND_SAVE_VALUE)

    if command_ok:
        time.sleep(5.0) # Beri jeda waktu yang cukup lama untuk sensor memproses
        return True
    else:
        print(f"  - [GAGAL] Menulis perintah SIMPAN ke Reg {CALIBRATION_COMMAND_REGISTER}.")
        return False

def read_ph_value(unit_id: int) -> float | None:
    """Membaca nilai pH terkalibrasi dari register 3 (0x0003)."""
    client.unit_id = unit_id
    registers = client.read_holding_registers(3, 1) 
    if registers and len(registers) > 0:
        return registers[0] / 10.0
    return None

# --- PROGRAM UTAMA KALIBRASI ---
print(f"==================================================")
print(f"  MODBUS PH CALIBRATION (1-Point + SAVE Command 0)")
print(f"==================================================")

try: 
    if not client.open():
        print("Gagal membuka koneksi Modbus.")
        exit()
    print("Koneksi Modbus berhasil dibuka.\n")

    for unit_id in SLAVE_IDS:
        print(f"███ MEMULAI KALIBRASI SATU TITIK UNTUK SLAVE ID {unit_id} ███")
        
        for buffer_name, scaled_value in CALIBRATION_POINT.items():
            
            print(f"\n[STEP] SILAKAN CELUPKAN SENSOR ID {unit_id} KE LARUTAN BUFFER pH {buffer_name}!")
            input("   >>> Tekan ENTER setelah pembacaan sensor stabil...")
            
            if write_calibration_point_and_save(unit_id, buffer_name, scaled_value):
                
                # --- VERIFIKASI PEMBACAAN ---
                current_ph = read_ph_value(unit_id)
                if current_ph is not None:
                    print(f"   [SUKSES] Kalibrasi selesai. PH TERKALIBRASI: {current_ph:.3f}")
                else:
                    print(f"   [SUKSES] Kalibrasi selesai, namun gagal membaca kembali pH.")
            else:
                print(f"   [GAGAL TOTAL] Kalibrasi gagal untuk ID {unit_id}.")
                
            time.sleep(1)
            
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