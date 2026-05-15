"""
server_vps.py
=============
TCP Server Utama untuk VPS Google Cloud.

Arsitektur:
  HF2211 (TCP Client) --> Internet --> VPS:5000 (TCP Server - script ini)
  
  Main Thread:  socket.accept() loop (tidak pernah mati)
  Client Thread: handle_client() per koneksi masuk
                 ├── Buffer Modbus RTU
                 ├── Parsing Hex → sensor_dict
                 ├── Fuzzy Logic → rekomendasi tanaman
                 └── INSERT ke MySQL via pymysql

Cara menjalankan di VPS:
  python3 server_vps.py

Cara menjalankan sebagai service (systemd):
  Lihat komentar di bagian bawah file ini.
"""

import socket
import threading
import logging
import time
import sys
import os
from datetime import datetime

# ============================================================
# KONFIGURASI (ubah sesuai kebutuhan VPS Anda)
# ============================================================

SERVER_HOST   = '0.0.0.0'   # Dengarkan semua interface (termasuk IP publik)
SERVER_PORT   = 5000         # Port yang dibuka di firewall GCP
SLAVE_ID      = 1            # Slave ID sensor yang terhubung (ubah jika beda)
RECV_TIMEOUT  = 10           # Timeout socket per koneksi (detik)
RECONNECT_WAIT = 5           # Jeda sebelum accept koneksi baru (detik)
POLL_INTERVAL  = 2           # Interval kirim Modbus request ke sensor (detik)

# Konfigurasi Database
DB_CONFIG = {
    'host':     'localhost',
    'user':     'python_user',      # User khusus Python (dibuat via sudo mysql)
    'password': 'TugasAkhir123!',   # Password sesuai perintah CREATE USER
    'database': 'tanah_db',
    'port':     3306,
}

# ============================================================
# SETUP LOGGING
# ============================================================

os.makedirs('logs', exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.StreamHandler(sys.stdout),                      # Ke terminal
        logging.FileHandler('logs/server_vps.log', encoding='utf-8')  # Ke file
    ]
)
logger = logging.getLogger('server_vps')

# ============================================================
# IMPORT MODUL PROYEK
# ============================================================

# Tambahkan root project ke sys.path agar import src.* bisa jalan
# saat dijalankan dari direktori mana saja
_ROOT = os.path.dirname(os.path.abspath(__file__))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.core.modbus_parser import ModbusBufferHandler
from src.db.database_vps import DatabaseVPS
from src.fuzzy.fuzzy_logic import SoilFuzzyEvaluator


# ============================================================
# INISIALISASI KOMPONEN GLOBAL
# ============================================================

logger.info("=" * 60)
logger.info("  SISTEM MONITORING TANAH - VPS TCP SERVER")
logger.info("=" * 60)

# Database (satu instance, shared antar thread dengan lock)
_db_lock = threading.Lock()
db = DatabaseVPS(**DB_CONFIG)

# Fuzzy Logic (berat di awal, buat sekali saja)
logger.info("[INIT] Memuat Fuzzy Logic Mamdani...")
try:
    fuzzy = SoilFuzzyEvaluator()
    logger.info("[INIT] Fuzzy Logic siap.")
except Exception as e:
    logger.error(f"[INIT] Gagal memuat Fuzzy Logic: {e}")
    fuzzy = None

# Hubungkan ke database
logger.info("[INIT] Menghubungkan ke database...")
if not db.connect():
    logger.warning("[INIT] Database tidak terhubung saat startup. Akan retry saat ada data.")


# ============================================================
# MODBUS REQUEST BUILDER
# ============================================================

def crc16_modbus(data: bytes) -> int:
    """Hitung CRC16 Modbus (polynomial 0xA001)."""
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x0001:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
    return crc


# Transaction ID tidak diperlukan untuk RTU
def build_modbus_request(slave_id: int = 1, start_reg: int = 0, count: int = 8) -> bytes:
    """
    Buat frame Modbus RTU Read Holding Registers (FC=03).
    HF2211 dalam mode transparent meneruskan bytes ke RS485 as-is.
    Sensor hanya mengenali Modbus RTU native (8 bytes + CRC).

    Frame: [SlaveID][FC=03][StartReg Hi][StartReg Lo][Count Hi][Count Lo][CRC Lo][CRC Hi]
    Total: 8 bytes
    """
    import struct
    frame = struct.pack('>BBHH', slave_id, 0x03, start_reg, count)
    crc = crc16_modbus(frame)
    return frame + struct.pack('<H', crc)


# ============================================================
# HANDLER PER KONEKSI CLIENT
# ============================================================


def handle_client(conn: socket.socket, addr: tuple) -> None:
    """
    Menangani satu koneksi TCP dari HF2211.
    Dipanggil di thread terpisah setiap ada koneksi masuk.

    Args:
        conn: Socket koneksi client yang sudah di-accept
        addr: Tuple (IP, port) client
    """
    client_id = f"{addr[0]}:{addr[1]}"
    logger.info(f"[CONNECT] HF2211 terhubung dari {client_id}")
    logger.info(f"[POLL] Mode aktif: kirim Modbus TCP request setiap {POLL_INTERVAL}s ke Slave {SLAVE_ID}")

    buf = ModbusBufferHandler()
    conn.settimeout(RECV_TIMEOUT)
    stop_event = threading.Event()

    # ---- THREAD POLLING: kirim Modbus TCP request ke sensor via HF2211 gateway ----
    def poll_sensor():
        """Kirim Modbus TCP request ke HF2211 (gateway RTU↔TCP) setiap POLL_INTERVAL detik."""
        while not stop_event.is_set():
            try:
                request = build_modbus_request(slave_id=SLAVE_ID, start_reg=0, count=8)
                logger.debug(f"[POLL] Modbus TCP request: {request.hex()}")
                conn.sendall(request)
            except Exception as e:
                logger.info(f"[POLL] Koneksi terputus saat kirim request: {e}")
                break
            stop_event.wait(POLL_INTERVAL)

    poll_thread = threading.Thread(target=poll_sensor, daemon=True, name=f"poll-{client_id}")
    poll_thread.start()

    try:
        while True:
            # ---- TERIMA DATA RAW ----
            try:
                raw_chunk = conn.recv(256)
            except socket.timeout:
                logger.debug(f"[{client_id}] Timeout menunggu respons sensor...")
                continue
            except ConnectionResetError:
                logger.info(f"[DISCONNECT] {client_id} memutuskan koneksi (reset)")
                break

            if not raw_chunk:
                logger.info(f"[DISCONNECT] {client_id} menutup koneksi (EOF)")
                break

            logger.debug(f"[{client_id}] Terima {len(raw_chunk)} byte: {raw_chunk.hex()}")

            # ---- FEED KE BUFFER ----
            buf.feed(raw_chunk)

            # ---- COBA PARSING (abaikan request frame 8-byte, ambil response 19-byte) ----
            sensor_data = buf.try_parse()
            if sensor_data is None:
                continue

            # ---- DATA BERHASIL DI-PARSE ----
            ts = datetime.now()
            logger.info(
                f"[DATA] [{ts:%H:%M:%S}] Slave {SLAVE_ID} | "
                f"Kelembapan={sensor_data['kelembapan_tanah']}% | "
                f"Suhu={sensor_data['suhu']}°C | "
                f"pH={sensor_data['ph_tanah']} | "
                f"N={sensor_data['nitrogen']} | "
                f"P={sensor_data['fosfor']} | "
                f"K={sensor_data['kalium']} | "
                f"Sal={sensor_data.get('salinity', 0)}"
            )

            # ---- SIMPAN KE DATABASE ----
            with _db_lock:
                db.save_reading(sensor_data, slave_id=SLAVE_ID, timestamp=ts)

            # ---- FUZZY LOGIC: REKOMENDASI TANAMAN ----
            if fuzzy:
                try:
                    all_results = fuzzy.get_all_crop_recommendations(sensor_data)
                    if all_results:
                        logger.info("[FUZZY] Top 5 Rekomendasi Tanaman:")
                        for i, crop in enumerate(all_results[:5], 1):
                            logger.info(
                                f"         {i}. {crop['nama']:<15} "
                                f"Skor={crop['skor']}%  [{crop['status']}]"
                            )
                        with _db_lock:
                            db.save_recommendation(all_results, slave_id=SLAVE_ID, timestamp=ts)
                except Exception as e:
                    logger.error(f"[FUZZY] Error evaluasi: {e}")

    except Exception as e:
        logger.error(f"[ERROR] Error tak terduga dari {client_id}: {e}")
    finally:
        stop_event.set()
        buf.clear()
        try:
            conn.close()
        except Exception:
            pass
        logger.info(f"[DISCONNECT] Koneksi {client_id} ditutup.")


# ============================================================
# SERVER UTAMA
# ============================================================

class VPSTCPServer:
    """
    TCP Server yang robust dan tidak pernah mati.

    Fitur ketahanan:
    - SO_REUSEADDR: bisa restart langsung tanpa "Address already in use"
    - accept() loop: setiap klien ditangani di thread terpisah
    - Jika HF2211 disconnect → thread client mati, server tetap standby
    - try/except di setiap level untuk mencegah crash total
    """

    def __init__(self, host: str = SERVER_HOST, port: int = SERVER_PORT):
        self.host = host
        self.port = port
        self._running = False

    def start(self) -> None:
        """Mulai server dan masuk ke accept() loop selamanya."""
        self._running = True

        # Buat socket TCP
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_sock:

            # SO_REUSEADDR: izinkan bind ulang ke port yang sama setelah restart
            server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

            server_sock.bind((self.host, self.port))
            server_sock.listen(5)  # Antrean maksimum 5 koneksi masuk

            logger.info(f"[SERVER] Standby di port {self.port}. Menunggu HF2211...")
            logger.info("[SERVER] Tekan Ctrl+C untuk menghentikan.")

            while self._running:
                try:
                    # Terima koneksi baru (blocking)
                    conn, addr = server_sock.accept()

                    # Spawn thread baru untuk menangani klien ini
                    # daemon=True: thread otomatis mati jika program utama berhenti
                    t = threading.Thread(
                        target=handle_client,
                        args=(conn, addr),
                        daemon=True,
                        name=f"client-{addr[0]}"
                    )
                    t.start()

                except KeyboardInterrupt:
                    logger.info("\n[SERVER] Dihentikan oleh pengguna (Ctrl+C)")
                    self._running = False
                    break
                except OSError as e:
                    logger.error(f"[SERVER] Error socket: {e}")
                    if self._running:
                        time.sleep(RECONNECT_WAIT)

        logger.info("[SERVER] Server ditutup.")

    def stop(self) -> None:
        """Tandai server untuk berhenti (dari thread lain)."""
        self._running = False


# ============================================================
# ENTRY POINT
# ============================================================

def main():
    server = VPSTCPServer(host=SERVER_HOST, port=SERVER_PORT)
    try:
        server.start()
    except KeyboardInterrupt:
        pass
    finally:
        db.disconnect()
        logger.info("[SERVER] Cleanup selesai. Program berakhir.")


if __name__ == "__main__":
    main()


# ============================================================
# CATATAN DEPLOYMENT DI VPS (Ubuntu 22.04)
# ============================================================
#
# 1. Install dependencies:
#    pip3 install pymysql scikit-fuzzy numpy
#
# 2. Buka port di firewall GCP:
#    gcloud compute firewall-rules create allow-modbus \
#      --allow=tcp:5000 --direction=INGRESS
#
# 3. Jalankan manual (untuk testing):
#    python3 server_vps.py
#
# 4. Jalankan sebagai systemd service (agar auto-start & restart):
#    Buat file: /etc/systemd/system/tanah-monitor.service
#    ----
#    [Unit]
#    Description=Tanah Monitoring TCP Server
#    After=network.target mysql.service
#
#    [Service]
#    User=ubuntu
#    WorkingDirectory=/home/ubuntu/PA-Tanah
#    ExecStart=/usr/bin/python3 server_vps.py
#    Restart=always
#    RestartSec=5
#
#    [Install]
#    WantedBy=multi-user.target
#    ----
#    sudo systemctl enable tanah-monitor
#    sudo systemctl start tanah-monitor
#    sudo systemctl status tanah-monitor
#    journalctl -u tanah-monitor -f   # untuk lihat log realtime
