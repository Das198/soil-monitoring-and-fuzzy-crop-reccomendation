import os
import sys
import logging
import json
from datetime import datetime
from flask import Flask, render_template, jsonify
from flask_basicauth import BasicAuth

# Tambahkan root project ke sys.path agar import src.* bisa jalan
_ROOT = os.path.dirname(os.path.abspath(__file__))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.db.database_vps import DatabaseVPS

# Konfigurasi Database (Sama dengan server_vps.py)
DB_CONFIG = {
    'host':     'localhost',
    'user':     'python_user',
    'password': 'TugasAkhir123!',
    'database': 'tanah_db',
    'port':     3306,
}

# Setup Flask
app = Flask(__name__)

# ============================================================
# KONFIGURASI KEAMANAN (BASIC AUTH)
# ============================================================
# Mengamankan halaman agar bot/crawler tidak bisa masuk sembarangan
app.config['BASIC_AUTH_USERNAME'] = 'admin'
app.config['BASIC_AUTH_PASSWORD'] = 'RahasiaTanah123!'
app.config['BASIC_AUTH_FORCE'] = True  # Paksa login untuk semua route

basic_auth = BasicAuth(app)

# ============================================================
# INISIALISASI DATABASE
# ============================================================
db = DatabaseVPS(**DB_CONFIG)
db.connect()

@app.route('/')
def index():
    """Route utama untuk menampilkan UI web."""
    return render_template('index.html')

@app.route('/api/data')
def get_data():
    """API Endpoint untuk mengambil data terbaru via AJAX."""
    try:
        # Ambil data sensor terbaru
        sensor_data_list = db.get_recent_data(slave_ids=[1, 2, 3], limit=1)
        
        # Ambil rekomendasi terbaru
        rekomendasi_data = []
        if db._ensure_connected():
            with db._conn.cursor() as cur:
                # Ambil record terbaru dari tabel rekomendasi
                cur.execute("SELECT * FROM `rekomendasi` ORDER BY id DESC LIMIT 1")
                rec = cur.fetchone()
                
                if rec and rec[13]: # index 13 adalah data_json berdasarkan posisi skema di database_vps
                    try:
                        rekomendasi_data = json.loads(rec[13])
                    except Exception as e:
                        logging.error(f"Gagal parse JSON rekomendasi: {e}")

        response = {
            'status': 'success',
            'sensor': sensor_data_list[0] if sensor_data_list else None,
            'rekomendasi': rekomendasi_data if rekomendasi_data else [], # Semua tanaman
            'timestamp': datetime.now().isoformat()
        }
        return jsonify(response)
    except Exception as e:
        logging.error(f"Error fetching data: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

if __name__ == '__main__':
    # Mode Development
    app.run(host='0.0.0.0', port=8080, debug=True)
else:
    # Mode Production (dipanggil oleh Waitress)
    # logger setup untuk gunicorn/waitress
    gunicorn_logger = logging.getLogger('gunicorn.error')
    app.logger.handlers = gunicorn_logger.handlers
    app.logger.setLevel(gunicorn_logger.level)
