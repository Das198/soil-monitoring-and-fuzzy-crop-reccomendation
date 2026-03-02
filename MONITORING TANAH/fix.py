from pyModbusTCP.client import ModbusClient
import time

# --- KONFIGURASI MODBUS ---
# Ganti dengan alamat IP dan port yang benar dari perangkat HF2211 Anda
SERVER_HOST = "10.10.100.254"  # Ganti dengan IP Address HF2211 Anda
SERVER_PORT = 8899             # Ganti dengan Port TCP HF2211 Anda (Biasanya 502)
UNIT_ID = 3                    # Ganti dengan Unit ID (Slave ID) perangkat Anda

# --- KONFIGURASI PEMBACAAN DATA KONTINU ---
REGISTER_ADDRESS = 0           # Alamat register yang akan dibaca (Register 0)
REGISTER_COUNT = 1             # Hanya membaca 1 register (Nilai tunggal)
POLLING_INTERVAL = 1           # Interval pembacaan dalam detik (1 detik)

# Inisialisasi Klien Modbus TCP di luar loop untuk koneksi yang efisien
client = ModbusClient(
    host=SERVER_HOST, 
    port=SERVER_PORT, 
    unit_id=UNIT_ID, 
    auto_open=True, 
    auto_close=False  # Set ke False agar koneksi tetap terbuka selama loop
)

print(f"Mencoba koneksi ke {SERVER_HOST}:{SERVER_PORT}...")

try:
    # Buka koneksi awal
    if client.open():
        print("Koneksi Modbus berhasil dibuka.")
    else:
        print("Gagal membuka koneksi awal. Memastikan IP dan Port sudah benar.")
        exit()
        
    # --- Loop Pembacaan Kontinu ---
    while True:
        # Baca Holding Registers (Function Code 3)
        # client.read_holding_registers(alamat_mulai, jumlah_register)
        registers = client.read_holding_registers(REGISTER_ADDRESS, REGISTER_COUNT)

        # Periksa hasil pembacaan
        if registers:
            # Pembacaan berhasil, cetak data register pertama
            nilai_register_0 = registers[0]
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            print(f"[{timestamp}] Sukses! Nilai Register {REGISTER_ADDRESS}: {nilai_register_0}")
            
        else:
            # Gagal membaca (mungkin karena timeout atau koneksi putus)
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] GAGAL membaca register. Mencoba menghubungkan kembali...")
            # Coba buka koneksi lagi jika putus
            if not client.is_open:
                 client.open()

        # Jeda selama 1 detik sebelum pembacaan berikutnya
        time.sleep(POLLING_INTERVAL)

except KeyboardInterrupt:
    print("\nProgram dihentikan oleh pengguna (Ctrl+C).")
except Exception as e:
    print(f"\nTerjadi kesalahan tak terduga: {e}")
    
finally:
    # Tutup koneksi saat program berakhir
    if client.is_open:
        client.close()
        print("Koneksi Modbus ditutup.")