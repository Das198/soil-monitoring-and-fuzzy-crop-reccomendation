# 🌱 Quick Start Guide - Sistem Monitoring Tanah

## 1️⃣ Setup Awal

### Aktivasi Virtual Environment
```bash
# Windows
.venv\Scripts\Activate.ps1

# Linux/Mac
source .venv/bin/activate
```

### Install Dependencies (jika belum)
```bash
pip install -r requirements.txt
```

---

## 2️⃣ Konfigurasi

Edit file `src/config.py` untuk menyesuaikan:

```python
# Modbus Gateway
MODBUS_SERVER_HOST = "10.10.100.254"
MODBUS_SERVER_PORT = 8899

# Sensor yang aktif
MODBUS_SLAVE_IDS = [1, 2]

# Node-RED
NODE_RED_IP = "127.0.0.1"
NODE_RED_PORT = 5020

# Database (optional)
DB_HOST = "localhost"
DB_NAME = "tanah_monitoring"
```

---

## 3️⃣ Menjalankan Sistem

### Mode Monitoring (Real-time)
Membaca sensor dan mengirim ke Node-RED:
```bash
python main.py
```

Output:
```
============================================================
🌱 SISTEM MONITORING TANAH - MEMULAI
============================================================
✓ Koneksi Modbus berhasil dibuka
✓ Terkoneksi ke Node-RED di 127.0.0.1:5020

📊 --- 2026-04-15 10:30:45 - Mulai Siklus Pembacaan ---
[ID 1] ✅ SUKSES:
  > Kelembapan Tanah: 50.5
  > Suhu: 25.0
  > Ph Tanah: 6.8
  > Nitrogen: 100
[ID 1] ✓ Data terkirim ke Node-RED
```

### Mode Kalibrasi pH
Kalibrasi sensor pH dengan buffer standar:
```bash
python -m src.calibration.calibrator
```

Menu:
```
System monitoring tanah - Mode Kalibrasi pH
Masukkan Slave ID: 1

1. Kalibrasi Single Point
2. Kalibrasi Multi-Point
Pilih mode (1/2): 2
```

### Mode Fuzzy Logic Test
Evaluasi kesehatan tanah:
```bash
python -m src.fuzzy.fuzzy_logic
```

Output:
```
✓ Hasil evaluasi: {'health_score': 75.23, 'rating': 'Baik', ...}
✓ Kompatibilitas dengan Jagung: {ph_tanah: {value: 6.5, status: 'OK', ...}, ...}
```

---

## 4️⃣ Struktur Module

```
src/
├── config.py              ← Edit di sini untuk konfigurasi
├── main.py                ← Jalankan untuk monitoring
├── core/
│   ├── modbus_handler.py  ← Komunikasi Modbus
│   ├── sensor_data.py     ← Proses data sensor
│   └── node_red_sender.py ← Kirim ke Node-RED
├── calibration/
│   └── calibrator.py      ← Kalibrasi pH
├── fuzzy/
│   └── fuzzy_logic.py     ← Fuzzy logic
├── db/
│   └── database.py        ← Database MySQL
└── utils/
    └── logger.py          ← Logging
```

---

## 5️⃣ Troubleshooting

### ❌ "Koneksi Modbus gagal"
```
Cek:
1. IP Address Modbus: MODBUS_SERVER_HOST
2. Port Modbus: MODBUS_SERVER_PORT
3. Slave ID yang aktif: MODBUS_SLAVE_IDS
4. Modbus Gateway sudah nyala?
```

### ❌ "Node-RED tidak terkoneksi"
```
Cek:
1. IP Node-RED: NODE_RED_IP
2. Port Node-RED: NODE_RED_PORT
3. Node-RED sudah running?
4. (Sistem akan tetap jalan, data tidak terkirim)
```

### ❌ ModuleNotFoundError
```bash
# Pastikan menjalankan dari root folder
cd "PA Tanah"
python main.py  # Bukan: python src/main.py
```

### ❌ Database connection failed
```
Database opsional. Untuk menggunakan:
1. Install MySQL
2. Buat database: CREATE DATABASE tanah_monitoring;
3. Update DB_HOST, DB_USER, DB_PASSWORD di config.py
```

---

## 6️⃣ File Penting

| File | Fungsi |
|------|--------|
| `main.py` | Entry point utama (jalankan ini) |
| `src/config.py` | Konfigurasi semua parameter |
| `requirements.txt` | Python packages |
| `README.md` | Dokumentasi lengkap |
| `tanah_db.sql` | SQL schema (untuk MySQL) |

---

## 7️⃣ Monitoring di Terminal

```bash
# View real-time output
python main.py

# View logs file
tail -f logs/monitoring.log  # Linux/Mac
Get-Content logs/monitoring.log -Wait  # Windows PowerShell
```

---

## 8️⃣ Data Format JSON (ke Node-RED)

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

## 9️⃣ Keyboard Shortcuts

```
Ctrl+C  → Hentikan program (graceful shutdown)
```

---

## 🔟 Next Steps

1. ✅ Edit `src/config.py` dengan parameter Anda
2. ✅ Jalankan `python main.py`
3. ✅ Monitor output di terminal/log file
4. ✅ Cek data di Node-RED dashboard
5. ✅ (Optional) Setup database MySQL

---

**Happy Monitoring! 🌱**
