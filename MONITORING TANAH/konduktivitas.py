from pyModbusTCP.client import ModbusClient
import time
from typing import List

# --- KONFIGURASI MODBUS ---
SERVER_HOST = "10.10.100.254" 
SERVER_PORT = 8899 
SLAVE_IDS: List[int] = [1] 

# --- KONFIGURASI KALIBRASI KONDUKTIVITAS (EC) ---
EC_CALIBRATION_REGISTER: int = 82   # Alamat 0x0052 (Desimal 82) untuk Conductivity Offset
EC_TARGET_VALUE: int = 1413         # NILAI BARU: 1413 us/cm (Resolusi 1, tanpa skala)
READ_REGISTER_EC: int = 5           # Asumsi: Register 0x0005 untuk membaca nilai EC

# --- INISIALISASI KLIEN MODBUS ---
client = ModbusClient(
    host=SERVER_HOST, 
    port=SERVER_PORT, 
    auto_open=True, 
    auto_close=False,
    timeout=5.0 
)

def calibrate_ec_step(unit_id: int, target_value: int) -> bool:
    """Melakukan penulisan kalibrasi Konduktivitas ke register 0x0052 (82)."""
    client.unit_id = unit_id
    
    print(f"  - Mencoba menulis nilai target EC ({target_value}) ke Reg 0x0052 (82)...")
    
    # Menulis nilai 1413 (tanpa skala)
    is_ok = client.write_single_register(EC_CALIBRATION_REGISTER, target_value)

    if is_ok:
        time.sleep(5.0) # Jeda waktu untuk sensor memproses
        return True
    else:
        print(f"  - [GAGAL] Gagal menulis nilai ke Reg {EC_CALIBRATION_REGISTER}.")
        return False

def read_ec_value(unit_id: int) -> int | None:
    """Membaca nilai EC terkalibrasi dari register 0x0005 (Resolusi 1)."""
    client.unit_id = unit_id
    registers = client.read_holding_registers(READ_REGISTER_EC, 1) 
    if registers and len(registers) > 0:
        # TIDAK PERLU dibagi 10 karena resolusi = 1
        return registers[0] 
    return None

# --- PROGRAM UTAMA KALIBRASI EC ---
print(f"==================================================")
print(f"  MODBUS KONDUKTIVITAS (EC) CALIBRATION (Reg 82)  ")
print(f"==================================================")
print(f"Nilai Target Kalibrasi: {EC_TARGET_VALUE} us/cm (Resolusi 1)")


try: 
    if not client.open():
        print("Gagal membuka koneksi Modbus.")
        exit()
    print("Koneksi Modbus berhasil dibuka.\n")

    for unit_id in SLAVE_IDS:
        print(f"███ MEMULAI KALIBRASI EC UNTUK SLAVE ID {unit_id} ███")
        
        print(f"\n[STEP] SILAKAN CELUPKAN SENSOR ID {unit_id} KE LARUTAN BUFFER 1413 us/cm!")
        input("   >>> Tekan ENTER setelah pembacaan sensor stabil...")
        
        if calibrate_ec_step(unit_id, EC_TARGET_VALUE):
            current_ec = read_ec_value(unit_id)
            
            # Verifikasi: Nilai harus mendekati 1413 us/cm
            if current_ec is not None:
                print(f"   [SUKSES] Kalibrasi selesai. EC TERKALIBRASI: {current_ec} us/cm")
                
                # Periksa Akurasi (toleransi 5%)
                if 1342 < current_ec < 1484:
                    print("   [AKURAT] Pembacaan dalam rentang toleransi 5% dari 1413 us/cm.")
                else:
                    print("   [PERHATIAN] Pembacaan di luar rentang toleransi. Ulangi kalibrasi.")

            else:
                print(f"   [Gagal Baca] Perintah write berhasil, namun gagal membaca kembali nilai EC.")

        print(f"\nKALIBRASI EC ID {unit_id} SELESAI.")
        print("-" * 40)

except KeyboardInterrupt: 
    print("\nProgram dihentikan oleh pengguna (Ctrl+C).")
except Exception as e: 
    print(f"\nTerjadi kesalahan tak terduga: {e}")
    
finally: 
    if client.is_open:
        client.close()
        print("Koneksi Modbus ditutup.")