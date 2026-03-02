from pyModbusTCP.client import ModbusClient
import time

# --- KONFIGURASI MODBUS ---
SERVER_HOST = "10.10.100.254"  # Ganti dengan IP Address HF2211 Anda
SERVER_PORT = 8899             # Ganti dengan Port TCP HF2211 Anda
SLAVE_IDS = [1, 2, 3]          # Daftar Slave ID yang akan dibaca (ID 1 sampai 3)

# --- KONFIGURASI PEMBACAAN DATA KONTINU ---
REGISTER_START_ADDRESS = 0     # Alamat awal pembacaan
REGISTER_COUNT = 7             # Jumlah register yang akan dibaca (0 hingga 6)
POLLING_INTERVAL = 1           # Interval total pembacaan dalam detik (1 detik per siklus 3 slave)

# Inisialisasi Klien Modbus TCP
# Catatan: unit_id awal tidak terlalu penting karena akan disetel di setiap panggilan read_holding_registers
client = ModbusClient(
    host=SERVER_HOST, 
    port=SERVER_PORT, 
    auto_open=True, 
    auto_close=False
)

print(f"Mencoba koneksi ke {SERVER_HOST}:{SERVER_PORT}...")

try:
    # Buka koneksi awal
    if client.open():
        print("Koneksi Modbus berhasil dibuka.")
        print(f"Memulai pembacaan kontinu untuk Slave ID: {SLAVE_IDS}")
    else:
        print("Gagal membuka koneksi awal. Memastikan IP dan Port sudah benar.")
        exit()
        
    # --- Loop Pembacaan Kontinu ---
    while True:
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        print(f"\n--- {timestamp} - Mulai Siklus Pembacaan ---")
        
        # 1. ULANGI PEMBACAAN UNTUK SETIAP SLAVE ID
        for unit_id in SLAVE_IDS:
            
            # Set unit_id untuk permintaan Modbus saat ini
            client.unit_id = unit_id
            
            # Baca Holding Registers (Function Code 3)
            # Akan membaca 7 register, dimulai dari alamat 0, untuk Slave ID saat ini
            registers = client.read_holding_registers(REGISTER_START_ADDRESS, REGISTER_COUNT)

            # Periksa hasil pembacaan
            if registers:
                # Pembacaan berhasil
                print(f"[ID {unit_id}] SUKSES: Nilai Register {REGISTER_START_ADDRESS} hingga {REGISTER_START_ADDRESS + REGISTER_COUNT - 1}:")
                
                # Mencetak setiap nilai register secara terpisah
                for i, value in enumerate(registers):
                    address = REGISTER_START_ADDRESS + i
                    print(f"  > Register {address}: {value}")
                
            else:
                # Gagal membaca
                print(f"[ID {unit_id}] GAGAL membaca register. Periksa koneksi ke slave ini.")
                
                # Coba buka koneksi lagi jika putus (hanya TCP)
                if not client.is_open:
                     client.open()

        # 2. Jeda selama 1 detik setelah menyelesaikan pembacaan SEMUA slave
        print("--- Akhir Siklus. Menunggu 1 detik. ---")
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