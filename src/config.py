"""
Konfigurasi Global untuk Sistem Monitoring Tanah
"""

# ============================================
# KONFIGURASI MODBUS TCP
# ============================================
MODBUS_SERVER_HOST = "10.17.41.27"   # IP Address HF2211 (WiFi Kampus)
MODBUS_SERVER_PORT = 8899             # Port TCP HF2211
MODBUS_TIMEOUT = 5.0                  # Timeout koneksi (detik)
MODBUS_SLAVE_IDS = [1, 2]             # Daftar Slave ID (Sensor 3 rusak)

# ============================================
# KONFIGURASI PEMBACAAN REGISTER
# ============================================
REGISTER_START_ADDRESS = 0
REGISTER_COUNT = 8                     # Total 8 register (0-7)
POLLING_INTERVAL = 1                   # Interval pembacaan dalam detik
INTER_SLAVE_DELAY = 0.1                # Delay antar slave (detik)
INTER_CYCLE_DELAY = 2                  # Delay antar siklus (detik)

# ============================================
# PETA NAMA REGISTER
# ============================================
REGISTER_MAP = {
    "kelembapan_tanah": 0,
    "suhu": 1,
    "konduktivitas": 2,
    "ph_tanah": 3,
    "nitrogen": 4,
    "fosfor": 5,
    "kalium": 6,
    "salinity": 7
}

# ============================================
# PARAMETER YANG MEMBUTUHKAN SCALING 0.1
# ============================================
SCALED_PARAMETERS = ["suhu", "kelembapan_tanah", "ph_tanah"]

# ============================================
# KONFIGURASI NODE-RED (TCP)
# ============================================
NODE_RED_IP = "127.0.0.1"              # Localhost atau IP Node-RED
NODE_RED_PORT = 5020                   # Port TCP untuk data sensor
NODE_RED_TIMEOUT = 5.0                 # Timeout koneksi (detik)

# ============================================
# KONFIGURASI COMMAND LISTENER (TCP SERVER LOKAL)
# ============================================
COMMAND_SERVER_IP = "127.0.0.1"        # IP untuk TCP Server lokal
COMMAND_SERVER_PORT = 5021             # Port menerima command (START/STOP)

# ============================================
# KONFIGURASI KALIBRASI PH
# ============================================
PH_CALIBRATION_REGISTER = 83           # 0x0053: PH offset
PH_COMMAND_REGISTER = 84               # 0x0054: Perintah SIMPAN/KELUAR
PH_COMMAND_SAVE = 0                    # Nilai perintah SIMPAN

CALIBRATION_POINT = {
    "6.86 (Titik Netral)": 7,
    "4.01 (Titik Asam)": 4,
    "9.18 (Titik Basa)": 9
}

# ============================================
# KONFIGURASI DATABASE
# ============================================
DB_HOST = "localhost"
DB_USER = "root"
DB_PASSWORD = ""
DB_NAME = "tanah_db"
DB_CHARSET = "utf8mb4"

# ============================================
# KONFIGURASI FILE
# ============================================
EXCEL_FILENAME = "data_sensor_tanah.xlsx"
EXCEL_SHEET_NAME = "Data Pembacaan Sensor"

# ============================================
# KONFIGURASI LOGGING
# ============================================
LOG_LEVEL = "INFO"
LOG_FILE = "logs/monitoring.log"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# ============================================
# DATA KEBUTUHAN TANAMAN
# ============================================
import os
import csv

CROP_REQUIREMENTS = {}
_csv_path = os.path.join(os.path.dirname(__file__), 'fuzzy', 'Tabel_Parameter_Tanaman.csv')

if os.path.exists(_csv_path):
    with open(_csv_path, 'r', encoding='utf-8') as _f:
        _reader = csv.DictReader(_f)
        for _row in _reader:
            try:
                _crop = _row.get('Nama Tanaman (Label)', '').strip()
                if not _crop:
                    continue
                    
                def _parse_range(val_str):
                    parts = str(val_str).split('-')
                    if len(parts) == 2:
                        return [float(parts[0].strip()), float(parts[1].strip())]
                    return [0.0, 0.0]
                
                CROP_REQUIREMENTS[_crop] = {
                    "n": _parse_range(_row.get('Nitrogen (N)', '0-0')),
                    "p": _parse_range(_row.get('Fosfor (P)', '0-0')),
                    "k": _parse_range(_row.get('Kalium (K)', '0-0')),
                    "temp": _parse_range(_row.get('Suhu (°C)', '0-0')),
                    "moist": _parse_range(_row.get('Kelembapan (%)', '0-0')),
                    "ph": _parse_range(_row.get('pH Tanah', '0-0')),
                    # Memasukkan salinity default karena data CSV tidak memiliki kolom ini
                    "sal": [0.0, 2.5]
                }
            except Exception as e:
                pass
else:
    # Fallback default jika file CSV belum terbuat/terhapus
    CROP_REQUIREMENTS = {
        "Jagung": {"ph": [5.5, 7.0], "temp": [18, 27], "moist": [55, 75], "n": [60, 100], "p": [35, 60], "k": [15, 25], "sal": [0, 2]},
        "Semangka": {"ph": [6.0, 7.0], "temp": [24, 27], "moist": [80, 90], "n": [80, 120], "p": [5, 30], "k": [45, 55], "sal": [0, 1.5]}
    }

