"""
sim_hf2211.py
=============
Skrip simulasi HF2211 untuk testing server_vps.py secara lokal.

Cara pakai:
  1. Jalankan server_vps.py di satu terminal:
       python server_vps.py
  2. Jalankan skrip ini di terminal lain:
       python sim_hf2211.py

Skrip ini akan mengirimkan frame Modbus RTU valid setiap 2 detik.
"""

import socket
import time
import struct

# ============================================================
# KONFIGURASI
# ============================================================
SERVER_IP   = '35.199.176.176'  # IP Publik VPS Google Cloud
SERVER_PORT = 5000
INTERVAL    = 2  # Kirim data setiap N detik


def crc16_modbus(data: bytes) -> int:
    """Hitung CRC16 Modbus."""
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x0001:
                crc >>= 1
                crc ^= 0xA001
            else:
                crc >>= 1
    return crc


def build_modbus_frame(
    slave_id: int = 1,
    kelembapan: float = 45.2,   # %
    suhu: float = 27.5,          # °C
    ec: int = 312,               # µS/cm
    ph: float = 6.8,
    nitrogen: int = 85,          # mg/kg
    fosfor: int = 42,
    kalium: int = 130
) -> bytes:
    """
    Buat frame Modbus RTU response yang valid.
    
    Format:
    [SlaveID][FC=03][ByteCount=14][7 register × 2 byte][CRC Low][CRC High]
    """
    # Konversi nilai ke raw register integer
    reg_kelembapan = int(kelembapan * 10)
    reg_suhu       = int(suhu * 10)
    reg_ec         = int(ec)
    reg_ph         = int(ph * 10)
    reg_n          = int(nitrogen)
    reg_p          = int(fosfor)
    reg_k          = int(kalium)

    byte_count = 14  # 7 register × 2 byte

    # Pack header + data (Big Endian unsigned short untuk setiap register)
    frame_without_crc = struct.pack(
        '>BBB7H',
        slave_id,    # Slave ID
        0x03,        # Function Code
        byte_count,  # Byte Count
        reg_kelembapan, reg_suhu, reg_ec, reg_ph,
        reg_n, reg_p, reg_k
    )

    # Hitung dan tambahkan CRC (Little Endian: Low byte dulu)
    crc = crc16_modbus(frame_without_crc)
    crc_low  = crc & 0xFF
    crc_high = (crc >> 8) & 0xFF

    frame = frame_without_crc + bytes([crc_low, crc_high])
    return frame


def main():
    print(f"[SIM] Menghubungkan ke {SERVER_IP}:{SERVER_PORT}...")

    # Variabel untuk simulasi perubahan nilai
    iteration = 0

    while True:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((SERVER_IP, SERVER_PORT))
                print(f"[SIM] Terhubung! Mulai kirim data Modbus RTU setiap {INTERVAL} detik.")

                while True:
                    # Variasikan nilai sedikit agar terlihat dinamis
                    frame = build_modbus_frame(
                        slave_id=1,
                        kelembapan=45.2 + (iteration % 10) * 0.5,
                        suhu=27.5 + (iteration % 5) * 0.1,
                        ec=310 + iteration,
                        ph=6.8 - (iteration % 3) * 0.1,
                        nitrogen=85 + (iteration % 20),
                        fosfor=42 + (iteration % 10),
                        kalium=130 + (iteration % 15)
                    )

                    print(f"[SIM] Kirim frame #{iteration+1}: {frame.hex()}")
                    s.sendall(frame)

                    iteration += 1
                    time.sleep(INTERVAL)

        except ConnectionRefusedError:
            print(f"[SIM] Server tidak bisa dihubungi, retry dalam 5 detik...")
            time.sleep(5)
        except BrokenPipeError:
            print("[SIM] Koneksi terputus, reconnect...")
            time.sleep(2)
        except KeyboardInterrupt:
            print("\n[SIM] Simulasi dihentikan.")
            break


if __name__ == "__main__":
    main()
