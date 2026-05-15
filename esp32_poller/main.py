"""
esp32_poller/main.py
====================
MicroPython script untuk ESP32 sebagai Modbus TCP poller.
Menggantikan peran poller_bg.py secara permanen di lapangan.

Hardware:
  - ESP32 (NodeMCU, WROOM, dll.)
  - Sumber daya: USB 5V / powerbank / baterai + TP4056
  - Terhubung ke WiFi yang sama dengan HF2211

Flash MicroPython ke ESP32:
  1. Download firmware: https://micropython.org/download/esp32/
  2. esptool.py --chip esp32 erase_flash
  3. esptool.py --chip esp32 write_flash -z 0x1000 esp32.bin
  4. Upload file ini dengan: ampy put main.py / mpremote copy main.py

Cara upload ke ESP32:
  pip install mpremote
  mpremote connect COMx cp main.py :main.py
"""

import network
import socket
import time
import struct
import machine

# LED Indikator (GPIO 2, active LOW pada ESP8266)
led = machine.Pin(2, machine.Pin.OUT)
led.value(1)  # Matikan LED awal


# ============================================================
# KONFIGURASI — SESUAIKAN INI
# ============================================================
WIFI_SSID     = 'DTEO-VOKASI'   # SSID WiFi yang sama dengan HF2211
WIFI_PASSWORD = 'TEO123456'      # Password WiFi

HF2211_IP   = '10.17.41.27'   # IP HF2211 (dari scan_full.py)
HF2211_PORT = 8899             # Port netp HF2211
SLAVE_ID    = 2                # Slave ID sensor aktif (sensor 1 rusak)
POLL_INTERVAL = 2              # detik antar poll
RECONNECT_DELAY = 10           # detik sebelum reconnect WiFi
AUTO_SCAN   = True             # Scan otomatis jika IP HF2211 tidak ditemukan
# ============================================================


def build_modbus_tcp_request(slave_id, start_reg, count, tx_id=1):
    """
    Bangun Modbus TCP request (MBAP header + PDU).
    Sama seperti yang dilakukan pyModbusTCP di laptop.
    """
    pdu  = bytes([slave_id, 0x03])            # Function Code 03 (Read Holding Registers)
    pdu += struct.pack('>H', start_reg)        # Start register (2 bytes big-endian)
    pdu += struct.pack('>H', count)            # Register count
    # MBAP Header: Transaction ID (2B) + Protocol (00 00) + Length (2B)
    mbap = struct.pack('>H', tx_id) + b'\x00\x00' + struct.pack('>H', len(pdu))
    return mbap + pdu


def connect_wifi():
    """Hubungkan ke WiFi, tunggu sampai konek."""
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if wlan.isconnected():
        return wlan

    print('[WiFi] Menghubungkan ke', WIFI_SSID, '...')
    wlan.connect(WIFI_SSID, WIFI_PASSWORD)

    timeout = 15  # detik
    while not wlan.isconnected() and timeout > 0:
        time.sleep(1)
        timeout -= 1
        print('[WiFi] Menunggu...', timeout)

    if wlan.isconnected():
        print('[WiFi] Terhubung! IP:', wlan.ifconfig()[0])
    else:
        print('[WiFi] GAGAL terhubung!')
    return wlan


def scan_for_hf2211():
    """
    Scan subnet /24 lokal untuk cari HF2211 (port 8899 terbuka).
    Dipanggil otomatis jika koneksi ke HF2211_IP gagal.
    """
    wlan = network.WLAN(network.STA_IF)
    my_ip = wlan.ifconfig()[0]          # e.g. '10.17.41.158'
    parts = my_ip.rsplit('.', 1)         # ['10.17.41', '158']
    base  = parts[0]                     # '10.17.41'
    print('[SCAN] Mencari HF2211 di %s.1-254 ...' % base)

    for i in range(1, 255):
        ip = '%s.%d' % (base, i)
        s = socket.socket()
        s.settimeout(0.3)
        try:
            s.connect((ip, HF2211_PORT))
            s.close()
            print('[SCAN] HF2211 ditemukan di:', ip)
            return ip
        except OSError:
            pass
        finally:
            try: s.close()
            except: pass

    print('[SCAN] HF2211 tidak ditemukan!')
    return None


def connect_hf2211(current_ip):
    """Buka koneksi persistent ke HF2211 netp. Auto-scan jika IP berubah."""
    global HF2211_IP
    target_ip = current_ip

    # Coba koneksi ke IP yang diketahui
    s = socket.socket()
    s.settimeout(5)
    try:
        s.connect((target_ip, HF2211_PORT))
    except OSError:
        s.close()
        # Jika gagal dan AUTO_SCAN aktif, cari IP baru
        if AUTO_SCAN:
            print('[HF2211] IP %s tidak reachable, mulai scan...' % target_ip)
            found = scan_for_hf2211()
            if found:
                HF2211_IP = found   # Update IP di memori
                target_ip = found
                s = socket.socket()
                s.settimeout(5)
                s.connect((target_ip, HF2211_PORT))
            else:
                raise OSError('HF2211 tidak ditemukan di jaringan')
        else:
            raise

    s.settimeout(3)
    print('[HF2211] Koneksi persistent ke %s:%d terbuka' % (target_ip, HF2211_PORT))
    return s


def run_poller():
    """
    Loop utama polling sensor dengan koneksi PERSISTENT.
    Koneksi TCP ke HF2211 dipertahankan terbuka — tidak close/reopen
    setiap poll (sama seperti pyModbusTCP auto_open=True, auto_close=False).
    Reconnect otomatis jika koneksi putus.
    """
    tx_id = 1
    ok    = 0
    fail  = 0
    sock  = None

    while True:
        # 1. Pastikan WiFi aktif
        wlan = network.WLAN(network.STA_IF)
        if not wlan.isconnected():
            led.value(0)  # Solid ON: Error WiFi
            print('[WiFi] Terputus, reconnect...')
            if sock:
                try: sock.close()
                except: pass
                sock = None
            connect_wifi()
            if not wlan.isconnected():
                time.sleep(RECONNECT_DELAY)
                continue
            led.value(1)  # Matikan LED jika konek


        # 2. Pastikan koneksi ke HF2211 aktif
        if sock is None:
            led.value(0)  # Solid ON: Error HF2211
            try:
                sock = connect_hf2211(HF2211_IP)
                led.value(1)  # Matikan LED jika konek
            except OSError as e:
                fail += 1
                print('[HF2211] Gagal konek: %s (%d kali)' % (str(e), fail))
                time.sleep(5)
                continue

        # 3. Kirim Modbus TCP request melalui koneksi yang sudah ada
        try:
            req = build_modbus_tcp_request(SLAVE_ID, 0, 8, tx_id)
            sock.send(req)
            resp = sock.recv(256)   # Terima & buang (VPS yang proses)

            # Blink LED saat berhasil kirim
            led.value(0)
            time.sleep(0.05)
            led.value(1)

            ok   += 1
            tx_id = (tx_id % 65535) + 1

            if ok % 30 == 1:
                print('[POLL] OK #%d | Gagal: %d' % (ok, fail))

        except OSError as e:
            fail += 1
            led.value(0)  # Solid ON: Error Poll
            print('[POLL] Koneksi error: %s — reconnect...' % str(e))
            try: sock.close()
            except: pass
            sock = None   # Akan reconnect di iterasi berikutnya

        time.sleep(POLL_INTERVAL)


# ============================================================
# MAIN
# ============================================================
print('=' * 40)
print('  ESP32 MODBUS POLLER')
print('  Target: %s:%d Slave %d' % (HF2211_IP, HF2211_PORT, SLAVE_ID))
print('=' * 40)

connect_wifi()
run_poller()
