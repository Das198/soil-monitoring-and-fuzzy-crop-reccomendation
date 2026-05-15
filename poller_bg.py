"""
poller_bg.py
============
Script ringan untuk menjaga HF2211 tetap polling sensor via netp.
Data sensor otomatis ter-push ke VPS via tcp_c HF2211.

Menggunakan pyModbusTCP (sama seperti main.py) agar kompatibel
dengan HF2211 netp (Protocol=Modbus = gateway Modbus TCP).

Jalankan di laptop/PC yang terhubung WiFi yang sama dengan HF2211:
    python poller_bg.py
"""
import time
import logging
import sys

from pyModbusTCP.client import ModbusClient

# ============ KONFIGURASI ============
HF2211_IP   = '10.17.41.27'   # IP HF2211 (dari scan_full.py)
HF2211_PORT = 8899             # Port netp HF2211 (TCP Server, Modbus TCP)
SLAVE_ID    = 2                # Slave ID sensor aktif (sensor 1 rusak)
INTERVAL    = 2                # detik antar poll
# =====================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger('poller')

logger.info("=" * 50)
logger.info(f"  POLLER: {HF2211_IP}:{HF2211_PORT} | Slave {SLAVE_ID} | {INTERVAL}s")
logger.info("  Tekan Ctrl+C untuk berhenti")
logger.info("=" * 50)

ok_count   = 0
fail_count = 0

client = ModbusClient(
    host=HF2211_IP,
    port=HF2211_PORT,
    unit_id=SLAVE_ID,
    auto_open=True,
    auto_close=False,
    timeout=5
)

try:
    while True:
        try:
            registers = client.read_holding_registers(0, 7)

            if registers:
                ok_count += 1
                if ok_count % 10 == 1:
                    logger.info(f"[OK] Poll #{ok_count} sukses | Gagal: {fail_count} | "
                                f"Kelembapan={registers[0]/10}%")
            else:
                fail_count += 1
                if fail_count <= 3 or fail_count % 10 == 0:
                    logger.warning(f"[WARN] Tidak ada response dari slave {SLAVE_ID} ({fail_count}x)")
                if not client.is_open:
                    client.open()

        except Exception as e:
            fail_count += 1
            if fail_count <= 3 or fail_count % 10 == 0:
                logger.warning(f"[ERROR] {e} ({fail_count}x)")
            try:
                client.close()
            except Exception:
                pass

        time.sleep(INTERVAL)

except KeyboardInterrupt:
    logger.info(f"\nDihentikan. Total poll: OK={ok_count}, Gagal={fail_count}")
    client.close()
