# 🌱 Sistem Monitoring Tanah - Struktur Modular

Proyek monitoring tanah real-time yang sudah direfactor menjadi struktur modular yang lebih rapi dan mudah di-maintain.

## 📁 Struktur Direktori

```
PA Tanah/
├── src/                          # ✨ KODE MODULAR AKTIF
│   ├── __init__.py              
│   ├── config.py                # Konfigurasi global (Modbus, Node-RED, Database, dll)
│   ├── core/                    # Core functionality
│   │   ├── __init__.py
│   │   ├── modbus_handler.py    # Koneksi & komunikasi Modbus TCP
│   │   ├── sensor_data.py       # Mapping & scaling data sensor
│   │   └── node_red_sender.py   # Pengiriman data ke Node-RED via TCP
│   ├── calibration/             # Module kalibrasi sensor pH
│   │   ├── __init__.py
│   │   └── calibrator.py        # Kalibrasi sensor pH CWT-SOIL
│   ├── fuzzy/                   # Module fuzzy logic
│   │   ├── __init__.py
│   │   └── fuzzy_logic.py       # Evaluasi kesehatan tanah dengan Fuzzy Logic
│   ├── db/                      # Module database
│   │   ├── __init__.py
│   │   └── database.py          # Handler MySQL untuk menyimpan data sensor
│   └── utils/                   # Utilities
│       ├── __init__.py
│       └── logger.py            # Centralized logging untuk semua modules
│
├── legacy/                      # 📦 FILE LAMA/EXPERIMENTAL (ARCHIVE)
│   └── README.md               # Daftar file-file yang perlu di-archive
│
├── main.py                      # 🚀 ENTRY POINT UTAMA
├── config.py                    # (Deprecated - gunakan src/config.py)
├── node-red.py                  # (Deprecated - gunakan main.py + src/)
├── requirements.txt             # Python dependencies
├── tanah_db.sql                 # SQL schema untuk database
├── flows.json                   # Node-RED flow configuration
└── README.md                    # (File ini)
```

## 🚀 Cara Menjalankan

### 1. Monitoring Real-time
```bash
python main.py
```
Program akan:
- ✓ Koneksi ke Modbus Gateway
- ✓ Koneksi ke Node-RED
- ✓ Membaca data sensor secara kontinyu
- ✓ Mengirim data ke Node-RED setiap siklus

### 2. Kalibrasi Sensor pH
```bash
python -m src.calibration.calibrator
```
Menu interaktif untuk:
- Kalibrasi single-point (satu buffer)
- Kalibrasi multi-point (6.86, 4.01, 9.18)

### 3. Test Fuzzy Logic
```bash
python -m src.fuzzy.fuzzy_logic
```
Mengevaluasi kesehatan tanah dan kompatibilitas dengan tanaman

### 4. Test Database
```bash
python -m src.db.database
```
Test koneksi dan operasi database MySQL

---

## 📦 Daftar Module

### `src/config.py`
Konfigurasi global sistem:
- Modbus TCP (host, port, slave IDs)
- Node-RED (IP, port)
- Database (host, user, password)
- Calibration points (pH)
- Crop requirements (kebutuhan tanaman)

### `src/core/modbus_handler.py`
**Class:** `ModbusHandler`
- `connect()` - Buka koneksi Modbus
- `disconnect()` - Tutup koneksi
- `read_registers()` - Baca holding registers
- `write_register()` - Tulis single register

### `src/core/sensor_data.py`
**Class:** `SensorData`
- `process_registers()` - Konversi raw register → sensor data
- `_scale_parameter()` - Apply scaling 0.1 ke parameter tertentu
- `format_output()` - Format data untuk pengiriman
- `get_readable_output()` - Generate text output yang mudah dibaca

### `src/core/node_red_sender.py`
**Class:** `NodeREDSender`
- `connect()` - Hubungkan ke Node-RED via TCP
- `disconnect()` - Putus koneksi
- `send_data()` - Kirim data sensor (JSON format)
- `send_batch()` - Kirim multiple data dalam batch

### `src/calibration/calibrator.py`
**Class:** `PHCalibrator`
- `connect()` - Koneksi ke Modbus
- `calibrate_single_point()` - Kalibrasi satu titik buffer
- `calibrate_multi_point()` - Kalibrasi 3 titik buffer secara berurutan
- `read_ph_value()` - Baca nilai pH dari sensor

### `src/fuzzy/fuzzy_logic.py`
**Class:** `SoilFuzzyEvaluator`
- `evaluate()` - Evaluasi kesehatan tanah (0-100 score)
- `check_crop_compatibility()` - Cek kesesuaian dengan kebutuhan tanaman
- `_get_rating()` - Konversi score ke rating deskriptif

### `src/db/database.py`
**Class:** `DatabaseHandler`
- `connect()` - Hubungkan ke MySQL database
- `disconnect()` - Putus koneksi
- `save_sensor_data()` - Simpan data sensor
- `get_recent_data()` - Ambil data terbaru
- `create_tables()` - Buat tabel jika belum ada

### `src/utils/logger.py`
- `get_logger()` - Dapatkan configured logger instance
- Logging ke console dan file (`logs/monitoring.log`)

### `main.py`
**Class:** `SoilMonitoringSystem`
- Orchestrate semua module
- Loop pembacaan kontinu dari Modbus
- Forward data ke Node-RED
- Error handling dan reconnection logic

---

## ⚙️ Konfigurasi

Edit file `src/config.py` untuk mengubah:

```python
# Modbus TCP
MODBUS_SERVER_HOST = "10.10.100.254"
MODBUS_SERVER_PORT = 8899
MODBUS_SLAVE_IDS = [1, 2]

# Node-RED
NODE_RED_IP = "127.0.0.1"
NODE_RED_PORT = 5020

# Database
DB_HOST = "localhost"
DB_USER = "root"
DB_PASSWORD = ""
DB_NAME = "tanah_monitoring"

# Polling interval
POLLING_INTERVAL = 1              # Detik
INTER_CYCLE_DELAY = 2             # Detik antar siklus
```

---

## 📊 Format Data JSON yang Dikirim ke Node-RED

```json
{
  "slave_id": 1,
  "timestamp": "2026-04-15 10:30:45",
  "data": {
    "kelembapan_tanah": 50.5,
    "suhu": 25.0,
    "konduktivitas": 2.5,
    "ph_tanah": 6.8,
    "nitrogen": 100,
    "fosfor": 30,
    "kalium": 100,
    "salinity": 1.0
  }
}
```

---

## 📋 File Lama yang Perlu Di-Archive

File-file berikut dapat dipindahkan ke `legacy/` folder karena sudah di-integrate ke struktur modular:

- `node-red.py` → Merged ke `main.py` + `src/core/`
- `kalibrasi.py` → Merged ke `src/calibration/calibrator.py`
- `kalibrasiBARU.py` → Merged ke `src/calibration/calibrator.py`
- `fuzzy.py` → Merged ke `src/fuzzy/fuzzy_logic.py`
- `cbfuzzy.py` → Merged ke `src/fuzzy/fuzzy_logic.py`
- `ambilData.py` → Reference: Membaca data sensor (sudah di-cover oleh `src/core/modbus_handler.py`)
- `ngambilData.py` → Reference: Pengambilan data
- `aturparameter.py` → Reference: Pengaturan parameter
- `parameterkoma.py` → Reference: Parameter dengan koma
- `konduktivitas.py` → Reference: Handling konduktivitas
- `fix.py`, `fixNemen.py`, `modifikasiBARU.py` → Experimental/fixes

---

## 🔄 Migrasi dari `node-red.py` ke `main.py`

**Sebelumnya:**
```bash
python node-red.py
```

**Sekarang:**
```bash
python main.py
```

Fungsionalitas tetap sama, tapi dengan struktur yang lebih bersih dan modular.

---

## 📝 Logging

Logs disimpan di `logs/monitoring.log` dengan format:
```
2026-04-15 10:30:45,123 - src.core.modbus_handler - INFO - ✓ Koneksi Modbus berhasil dibuka
```

---

## 🧪 Testing

Setiap module dapat di-test secara independen:

```bash
# Test Modbus handler
python -c "from src.core import ModbusHandler; m = ModbusHandler('10.10.100.254', 8899); print(m.connect())"

# Test Sensor data processor  
python -c "from src.core import SensorData; s = SensorData(); print(s.process_registers([50, 25, 2, 6, 100, 30, 100, 1]))"

# Test Node-RED sender
python -c "from src.core import NodeREDSender; n = NodeREDSender('127.0.0.1', 5020); print(n.connect())"
```

---

## ✨ Keuntungan Struktur Modular

✅ **Maintainability** - Kode lebih terorganisir  
✅ **Reusability** - Module dapat dipakai di berbagai script  
✅ **Testability** - Mudah test setiap komponen  
✅ **Scalability** - Mudah tambah fitur baru  
✅ **Separation of Concerns** - Setiap module punya tanggung jawab spesifik  

---

## 📦 Dependencies

Lihat `requirements.txt`:
- `pyModbusTCP` - Modbus TCP client
- `scikit-fuzzy` - Fuzzy logic library
- `numpy, scipy` - Numerical computing
- `openpyxl` - Excel operations
- `mysql-connector-python` (optional) - MySQL database

---

## 🐛 Troubleshooting

**Error: ModuleNotFoundError: No module named 'src'**
- Pastikan menjalankan dari root directory: `python main.py`

**Error: Koneksi Modbus gagal**
- Cek IP dan port di `src/config.py`
- Pastikan Modbus Gateway aktif dan terjangkau

**Error: Tidak bisa terhubung ke Node-RED**
- Node-RED akan retry otomatis
- Cek IP dan port Node-RED

**Error: MySQL connection failed**
- Database optional, sistem tetap jalan tanpa database
- Pastikan MySQL sudah installed dan berjalan

---

**Created:** 2026-04-15  
**Last Updated:** 2026-04-15  
**Version:** 1.0 (Modular Structure)
