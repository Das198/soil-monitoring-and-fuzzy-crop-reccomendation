"""
Konfigurasi Global untuk Sistem Monitoring Tanah
"""

# ============================================
# KONFIGURASI MODBUS TCP
# ============================================
MODBUS_SERVER_HOST = "10.17.40.85"   # IP Address HF2211 (WiFi Kampus)
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
DB_NAME = "tanah_monitoring"
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
CROP_REQUIREMENTS = {
    "Jagung": {
        "ph": [5.5, 7.0],
        "temp": [18, 27],
        "moist": [55, 75],
        "n": [60, 100],
        "p": [35, 60],
        "k": [15, 25],
        "sal": [0, 2]
    },
    "Semangka": {
        "ph": [6.0, 7.0],
        "temp": [24, 27],
        "moist": [80, 90],
        "n": [80, 120],
        "p": [5, 30],
        "k": [45, 55],
        "sal": [0, 1.5]
    },
    "Pisang": {
        "ph": [5.5, 6.5],
        "temp": [25, 30],
        "moist": [75, 85],
        "n": [80, 120],
        "p": [70, 95],
        "k": [45, 55],
        "sal": [0, 1]
    },
    "Mangga": {
        "ph": [4.5, 7.0],
        "temp": [27, 36],
        "moist": [45, 55],
        "n": [0, 40],
        "p": [15, 40],
        "k": [25, 35],
        "sal": [0, 2.5]
    }
}
