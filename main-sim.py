"""
main-sim.py
===========
Simulator Sistem Monitoring Tanah

Tujuan:
    Menggantikan hardware Modbus (HF2211) dengan generator data sintetis,
    sehingga seluruh alur data ke Node-RED tetap berjalan tanpa memerlukan
    perangkat fisik. Cocok untuk demo/showcase dashboard UI Node-RED.

Perbedaan dengan main.py:
    - TIDAK membutuhkan koneksi ke Modbus Gateway (HF2211)
    - TIDAK membutuhkan koneksi ke database (opsional, bisa diaktifkan)
    - Data sensor dibangkitkan secara sintetis dengan variasi realistis
    - Semua data tetap dikirim ke Node-RED via TCP (port 5020)
    - Semua command dari Node-RED tetap diterima (port 5021)
    - Command START/STOP/GENERATE/SET_SLAVES tetap berfungsi

Cara Pakai:
    1. Pastikan Node-RED sudah berjalan
    2. Jalankan: python main-sim.py
    3. Tekan tombol START di dashboard Node-RED
"""

import time
import json
import math
import random
from datetime import datetime
from src.config import (
    MODBUS_SLAVE_IDS,
    INTER_SLAVE_DELAY,
    INTER_CYCLE_DELAY,
    NODE_RED_IP,
    NODE_RED_PORT,
    NODE_RED_TIMEOUT,
    COMMAND_SERVER_IP,
    COMMAND_SERVER_PORT,
)
from src.core import NodeREDSender, CommandListener
from src.fuzzy.fuzzy_logic import SoilFuzzyEvaluator
from src.utils.logger import get_logger

logger = get_logger(__name__)


# ============================================================
# KONFIGURASI SIMULASI
# ============================================================

# Nilai tengah (baseline) per slave. Masing-masing slave disimulasikan
# dengan karakteristik tanah yang sedikit berbeda agar dashboard terlihat
# dinamis dan bervariasi.
SLAVE_BASELINES = {
    1: {
        "kelembapan_tanah": 52.0,   # %
        "suhu":             27.5,   # °C
        "konduktivitas":    320.0,  # µS/cm
        "ph_tanah":         6.8,    # pH
        "nitrogen":         88.0,   # mg/kg
        "fosfor":           44.0,   # mg/kg
        "kalium":           135.0,  # mg/kg
        "salinity":         1.1,    # dS/m
    },
    2: {
        "kelembapan_tanah": 38.0,
        "suhu":             29.0,
        "konduktivitas":    410.0,
        "ph_tanah":         5.9,
        "nitrogen":         62.0,
        "fosfor":           28.0,
        "kalium":           95.0,
        "salinity":         1.8,
    },
    3: {
        "kelembapan_tanah": 70.0,
        "suhu":             25.0,
        "konduktivitas":    250.0,
        "ph_tanah":         7.2,
        "nitrogen":         115.0,
        "fosfor":           55.0,
        "kalium":           180.0,
        "salinity":         0.7,
    },
}

# Amplitudo variasi sinusoidal untuk setiap parameter
WAVE_AMPLITUDE = {
    "kelembapan_tanah": 5.0,
    "suhu":             1.5,
    "konduktivitas":    30.0,
    "ph_tanah":         0.3,
    "nitrogen":         12.0,
    "fosfor":           8.0,
    "kalium":           20.0,
    "salinity":         0.3,
}

# Amplitudo noise acak per parameter
NOISE_AMPLITUDE = {
    "kelembapan_tanah": 0.8,
    "suhu":             0.2,
    "konduktivitas":    10.0,
    "ph_tanah":         0.05,
    "nitrogen":         3.0,
    "fosfor":           2.0,
    "kalium":           5.0,
    "salinity":         0.08,
}

# Batas clipping agar nilai tidak keluar rentang sensor fisik
PARAM_LIMITS = {
    "kelembapan_tanah": (0.0,   100.0),
    "suhu":             (10.0,  45.0),
    "konduktivitas":    (0.0,   2000.0),
    "ph_tanah":         (4.0,   8.5),
    "nitrogen":         (0.0,   250.0),
    "fosfor":           (0.0,   80.0),
    "kalium":           (0.0,   300.0),
    "salinity":         (0.0,   5.0),
}


# ============================================================
# GENERATOR DATA SINTETIS
# ============================================================

class SyntheticSensorGenerator:
    """
    Membangkitkan data sensor sintetis yang terlihat realistis.

    Setiap nilai merupakan kombinasi dari:
      1. Baseline (nilai tengah khas untuk lahan tersebut)
      2. Komponen sinusoidal (tren lambat, mirip perubahan cuaca/musim)
      3. Noise Gaussian (variasi acak kecil, mirip noise sensor nyata)
    """

    def __init__(self):
        self._tick = 0  # Counter siklus, bertambah setiap read_cycle()

    def generate(self, slave_id: int) -> dict:
        """
        Bangkitkan satu set data sensor untuk slave_id tertentu.

        Args:
            slave_id: ID slave Modbus (1, 2, atau 3)

        Returns:
            Dict data sensor dengan kunci sesuai REGISTER_MAP
        """
        baseline = SLAVE_BASELINES.get(slave_id, SLAVE_BASELINES[1])
        data = {}

        # Fasa berbeda per slave agar gelombang tidak sinkron sempurna
        phase_offset = (slave_id - 1) * math.pi / 3.0

        for param, base_val in baseline.items():
            amp   = WAVE_AMPLITUDE.get(param, 0.0)
            noise = NOISE_AMPLITUDE.get(param, 0.0)
            lo, hi = PARAM_LIMITS.get(param, (0.0, 9999.0))

            # Komponen sinusoidal — periode ~60 tick
            wave = amp * math.sin(self._tick * 0.1 + phase_offset)

            # Komponen noise Gaussian
            rand = random.gauss(0, noise)

            raw_val = base_val + wave + rand
            clamped = max(lo, min(hi, raw_val))
            data[param] = round(clamped, 2)

        return data

    def advance(self):
        """Majukan tick internal (dipanggil setiap siklus pembacaan)."""
        self._tick += 1


# ============================================================
# KELAS UTAMA SISTEM SIMULASI
# ============================================================

class SoilMonitoringSimulator:
    """
    Sistem simulasi monitoring tanah.

    Mereproduksi perilaku SoilMonitoringSystem dari main.py, namun
    menggantikan lapisan Modbus dengan SyntheticSensorGenerator.
    Koneksi ke Node-RED dan command listener tetap identik.
    """

    def __init__(self):
        """Inisialisasi semua komponen simulasi"""
        self.generator = SyntheticSensorGenerator()

        self.node_red = NodeREDSender(
            host=NODE_RED_IP,
            port=NODE_RED_PORT,
            timeout=NODE_RED_TIMEOUT
        )
        self.command_listener = CommandListener(
            host=COMMAND_SERVER_IP,
            port=COMMAND_SERVER_PORT,
            callback=self.handle_command
        )
        self.fuzzy = SoilFuzzyEvaluator()

        self.is_running   = False
        self.is_monitoring = False
        self.active_slaves = list(MODBUS_SLAVE_IDS)

        # Simpan data terakhir per slave agar GENERATE bisa pakai data terbaru
        self._last_data: dict[int, dict] = {}

    # ----------------------------------------------------------
    # COMMAND HANDLER (identik dengan main.py)
    # ----------------------------------------------------------

    def handle_command(self, cmd_str: str) -> None:
        """Handler untuk instruksi dari Node-RED (START/STOP/GENERATE/SET_SLAVES)"""
        cmd_str = cmd_str.strip()
        cmd = ""
        slaves = []

        try:
            data = json.loads(cmd_str)
            cmd = str(data.get("cmd", "")).strip().upper()
            if "slaves" in data:
                slaves = data["slaves"]
        except Exception:
            cmd = cmd_str.upper()

        if cmd == "SET_SLAVES":
            if isinstance(slaves, list):
                self.active_slaves = [
                    int(s) for s in slaves
                    if str(s).isdigit() or isinstance(s, int)
                ]
                logger.info(f"[SIM][MODE] Active Slaves → {self.active_slaves}")
            return

        elif cmd == "START":
            if not self.is_monitoring:
                self.is_monitoring = True
                logger.info(
                    f"[SIM][MODE] Beralih ke mode MONITORING. "
                    f"Siklus simulasi dimulai untuk slaves: {self.active_slaves}"
                )
            else:
                logger.info("[SIM][MODE] Sudah dalam mode MONITORING.")

        elif cmd == "STOP":
            if self.is_monitoring:
                self.is_monitoring = False
                logger.info("[SIM][MODE] Beralih ke mode STANDBY.")
            else:
                logger.info("[SIM][MODE] Sudah dalam mode STANDBY.")

        elif cmd == "GENERATE":
            logger.info(
                f"[SIM][ACTION] Tombol GENERATE ditekan! "
                f"Mengevaluasi untuk slaves aktif: {self.active_slaves}"
            )
            self._handle_generate()

        else:
            logger.warning(f"[SIM][WARN] Perintah tidak dikenal: '{cmd_str}'")

    def _handle_generate(self) -> None:
        """Jalankan fuzzy logic dan kirim rekomendasi ke Node-RED"""
        if not self.active_slaves:
            logger.warning("[SIM][Fuzzy] Tidak ada slave aktif.")
            if self.node_red.is_connected:
                self.node_red.send_data(
                    {"tipe": "rekomendasi_urutan", "data": []},
                    slave_id=0,
                    timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                )
            return

        # Ambil data terbaru dari cache (atau bangkitkan baru jika belum ada)
        merged = {}
        for sid in self.active_slaves:
            if sid not in self._last_data:
                self._last_data[sid] = self.generator.generate(sid)
            sdata = self._last_data[sid]
            for key, val in sdata.items():
                merged[key] = merged.get(key, 0) + val

        # Rata-ratakan antar slave
        n_slaves = len(self.active_slaves)
        avg_data = {k: round(v / n_slaves, 2) for k, v in merged.items()}
        logger.info(f"[SIM][Fuzzy] Data rata-rata untuk evaluasi: {avg_data}")

        results = self.fuzzy.get_all_crop_recommendations(avg_data)

        payload = {
            "tipe": "rekomendasi_urutan",
            "data": results
        }

        if self.node_red.is_connected:
            self.node_red.send_data(
                payload,
                slave_id=self.active_slaves[0],
                timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )
            logger.info("[SIM][Fuzzy] Rekomendasi tanaman terkirim ke Node-RED!")
        else:
            logger.warning("[SIM][Fuzzy] Node-RED tidak terhubung.")

    # ----------------------------------------------------------
    # STARTUP & SHUTDOWN
    # ----------------------------------------------------------

    def start(self) -> bool:
        """Inisialisasi dan mulai semua layanan"""
        logger.info("=" * 60)
        logger.info("[SIM] SIMULATOR MONITORING TANAH — MEMULAI")
        logger.info("=" * 60)
        logger.info("[SIM] Mode: SIMULASI (tanpa hardware Modbus)")
        logger.info(f"[SIM] Slaves yang disimulasikan: {self.active_slaves}")

        # Koneksikan ke Node-RED
        if not self.node_red.connect():
            logger.warning("[SIM][WARN] Gagal terhubung ke Node-RED (akan retry otomatis saat kirim data)")

        # Nyalakan Command Listener
        if not self.command_listener.start():
            logger.warning("[SIM][WARN] Gagal memulai Command Listener")

        self.is_running = True
        logger.info("[SIM][MODE] Sistem dalam mode STANDBY. Tekan START di dashboard Node-RED.")
        return True

    def stop(self) -> None:
        """Hentikan semua layanan dengan bersih"""
        logger.info("=" * 60)
        logger.info("[SIM] SIMULATOR MONITORING TANAH — BERHENTI")
        logger.info("=" * 60)
        self.is_running    = False
        self.is_monitoring = False
        self.command_listener.stop()
        self.node_red.disconnect()

    # ----------------------------------------------------------
    # READ CYCLE (menggantikan modbus.read_registers)
    # ----------------------------------------------------------

    def read_cycle(self) -> None:
        """
        Satu siklus pembacaan sintetis: bangkitkan data untuk setiap slave
        aktif, lalu kirim ke Node-RED persis seperti main.py.
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        logger.info(f"\n[SIM][DATA] --- {timestamp} - Mulai Siklus Simulasi ---")

        for unit_id in self.active_slaves:
            # 1. BANGKITKAN DATA SINTETIS (menggantikan modbus.read_registers)
            sensor_data = self.generator.generate(unit_id)

            # 2. SIMPAN KE CACHE untuk GENERATE
            self._last_data[unit_id] = sensor_data

            # 3. LOG DATA
            logger.info(f"[SIM][ID {unit_id}] Data sintetis:")
            for key, val in sensor_data.items():
                display_name = key.replace('_', ' ').title()
                logger.info(f"  > {display_name}: {val}")

            # 4. KIRIM KE NODE-RED (identik dengan main.py)
            if self.node_red.is_connected:
                if self.node_red.send_data(sensor_data, unit_id, timestamp):
                    logger.info(f"[SIM][ID {unit_id}] [OK] Data terkirim ke Node-RED")
                else:
                    logger.warning(f"[SIM][ID {unit_id}] [WARN] Gagal mengirim ke Node-RED")
            else:
                logger.debug(f"[SIM][ID {unit_id}] [SKIP] Node-RED tidak terkoneksi")

            time.sleep(INTER_SLAVE_DELAY)

        # Majukan waktu internal generator setelah satu siklus penuh
        self.generator.advance()

    # ----------------------------------------------------------
    # LOOP UTAMA
    # ----------------------------------------------------------

    def run(self) -> None:
        """Loop utama — identik strukturnya dengan main.py"""
        try:
            if not self.start():
                return

            while self.is_running:
                try:
                    if self.is_monitoring:
                        self.read_cycle()
                        time.sleep(INTER_CYCLE_DELAY)
                    else:
                        # Standby: hindari busy-loop
                        time.sleep(1)

                except KeyboardInterrupt:
                    logger.info("\n[SIM][STOP] Simulator dihentikan oleh pengguna (Ctrl+C)")
                    break
                except Exception as e:
                    logger.error(f"[SIM][ERROR] Error dalam siklus simulasi: {e}")
                    time.sleep(1)
                    continue

        except Exception as e:
            logger.error(f"[SIM][ERROR] Fatal error: {e}")
        finally:
            self.stop()


# ============================================================
# ENTRY POINT
# ============================================================

def main():
    """Entry point untuk simulator"""
    simulator = SoilMonitoringSimulator()
    simulator.run()


if __name__ == "__main__":
    main()
 