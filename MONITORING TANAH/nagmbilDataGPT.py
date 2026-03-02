from pymodbus.client import ModbusTcpClient
from pymodbus.exceptions import ModbusIOException
import time

# --- KONFIGURASI HF2211 ---
HOST = "10.10.100.254"   # IP HF2211
PORT = 8899              # Port TCP
SLAVE_ID = 3            # ID Modbus RS485 Slave
REGISTER_ADDRESS =    0  # Alamat register sensor
COUNT = 1                # Jumlah register dibaca

def baca_sensor_hf2211():
    client = ModbusTcpClient(host=HOST, port=PORT, timeout=3)
    print(f"Menghubungkan ke HF2211 di {HOST}:{PORT} ...")

    if not client.connect():
        print("❌ Gagal terhubung ke HF2211. Periksa IP dan jaringan.")
        return

    try:
        # Membaca Holding Register dari slave
        result = client.read_holding_registers(
            address=REGISTER_ADDRESS,
            count=COUNT,
            unit=SLAVE_ID
        )

        # Cek hasil pembacaan
        if isinstance(result, ModbusIOException) or not hasattr(result, "registers"):
            print("⚠️ Gagal membaca data: tidak ada respon dari perangkat.")
        else:
            data = result.registers
            print(f"✅ Data berhasil dibaca dari Unit ID {SLAVE_ID}: {data}")

            # Jika hanya 1 register, tampilkan nilainya langsung
            if COUNT == 1:
                print(f"Nilai tunggal: {data[0]}")

    except Exception as e:
        print(f"⚠️ Terjadi kesalahan selama operasi Modbus: {e}")

    finally:
        client.close()
        print("🔌 Koneksi ditutup.\n")


if __name__ == "__main__":
    while True:
        baca_sensor_hf2211()
        time.sleep(2)  # Delay antar pembacaan
