"""
test_domain_server.py
=====================
Server TCP sederhana untuk menguji apakah HF2211 bisa terhubung
menggunakan nama domain (DuckDNS) — dijalankan di laptop sementara VPS mati.

Cara pakai:
  1. Jalankan skrip ini di laptop
  2. Isi DuckDNS dengan IP publik laptop Anda
  3. Buka port forwarding di router: port 5000 → IP lokal laptop
  4. Ubah konfigurasi HF2211: Server = namadomain.duckdns.org, Port = 5000
  5. Lihat apakah koneksi dan data masuk di terminal ini
"""

import socket
import threading
import datetime

HOST = '0.0.0.0'   # Dengarkan semua interface
PORT = 5000

def get_local_ip():
    """Cari IP lokal laptop di jaringan."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 80))
        return s.getsockname()[0]
    except Exception:
        return '127.0.0.1'
    finally:
        s.close()

def handle_client(conn, addr):
    """Tangani satu koneksi masuk."""
    print(f"\n[{now()}] ✅ HF2211 TERHUBUNG dari {addr[0]}:{addr[1]}")
    print("-" * 50)
    try:
        while True:
            data = conn.recv(256)
            if not data:
                break
            print(f"[{now()}] Data diterima ({len(data)} byte):")
            print(f"  HEX  : {data.hex()}")
            print(f"  BYTES: {list(data)}")
    except Exception as e:
        print(f"[{now()}] Koneksi error: {e}")
    finally:
        conn.close()
        print(f"[{now()}] ❌ Koneksi {addr[0]} ditutup")

def now():
    return datetime.datetime.now().strftime('%H:%M:%S')

def main():
    local_ip = get_local_ip()

    print("=" * 55)
    print("  TEST SERVER - Uji Koneksi DuckDNS + HF2211")
    print("=" * 55)
    print(f"\n📍 IP Lokal Laptop  : {local_ip}")
    print(f"🔌 Listening Port   : {PORT}")
    print()
    print("📋 Langkah yang perlu dilakukan:")
    print(f"  1. Cari IP PUBLIK laptop Anda di: https://ifconfig.me")
    print(f"  2. Update DuckDNS dengan IP publik tersebut")
    print(f"  3. Buka port forwarding di router/modem:")
    print(f"     External Port 5000 → {local_ip}:{PORT}")
    print(f"  4. Set HF2211: Server=namadomain.duckdns.org, Port=5000")
    print()
    print("⏳ Menunggu koneksi dari HF2211...")
    print("-" * 55)

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as srv:
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind((HOST, PORT))
        srv.listen(5)
        try:
            while True:
                conn, addr = srv.accept()
                t = threading.Thread(target=handle_client, args=(conn, addr), daemon=True)
                t.start()
        except KeyboardInterrupt:
            print("\n[SERVER] Dihentikan (Ctrl+C)")

if __name__ == '__main__':
    main()
