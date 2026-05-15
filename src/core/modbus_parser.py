"""
modbus_parser.py
================
Modul untuk mem-parsing frame Modbus RTU mentah (raw bytes) yang diterima
dari sensor tanah 7-in-1 via HF2211 (Serial-to-WiFi).

STRUKTUR FRAME MODBUS RTU (Response baca register - FC 0x03):
=============================================================
Byte ke-  | Nama        | Keterangan
----------|-------------|------------------------------------------
0         | Slave ID    | Alamat sensor (biasanya 0x01)
1         | Function    | 0x03 = Read Holding Registers
2         | Byte Count  | Jumlah byte data = N_register × 2 = 14
3..4      | Reg 0 High, Low | Kelembapan (×0.1 %)
5..6      | Reg 1 High, Low | Suhu (×0.1 °C)
7..8      | Reg 2 High, Low | EC/Konduktivitas (µS/cm, tanpa scaling)
9..10     | Reg 3 High, Low | pH (×0.1)
11..12    | Reg 4 High, Low | Nitrogen N (mg/kg)
13..14    | Reg 5 High, Low | Fosfor P (mg/kg)
15..16    | Reg 6 High, Low | Kalium K (mg/kg)
17        | CRC Low     | Byte rendah CRC-16 (Modbus)
18        | CRC High    | Byte tinggi CRC-16 (Modbus)

Total frame: 19 byte (untuk 7 register)
"""

import struct
import logging

logger = logging.getLogger(__name__)

# ============================================================
# KONSTANTA FRAME MODBUS RTU
# ============================================================

# Panjang minimum frame: Slave ID (1) + FC (1) + Byte Count (1) + CRC (2) = 5 byte
MODBUS_MIN_FRAME_LEN = 5

# Indeks byte dalam frame
IDX_SLAVE_ID   = 0  # Byte 0: Slave ID
IDX_FUNC_CODE  = 1  # Byte 1: Function Code
IDX_BYTE_COUNT = 2  # Byte 2: Jumlah byte data
IDX_DATA_START = 3  # Byte 3: Mulai data register

# Jumlah register yang dibaca sensor ini (8 parameter termasuk Salinitas)
N_REGISTERS = 8

# Panjang frame yang diharapkan: 3 header + (7×2) data + 2 CRC = 19 byte
EXPECTED_FRAME_LEN = 3 + (N_REGISTERS * 2) + 2  # = 19 byte


# ============================================================
# FUNGSI CRC-16 MODBUS
# ============================================================

def _crc16_modbus(data: bytes) -> int:
    """
    Hitung CRC-16 menggunakan algoritma Modbus (polynomial 0xA001).

    Cara kerja:
    - CRC dimulai dari 0xFFFF
    - Setiap byte di-XOR ke CRC, lalu diproses 8 bit dengan memeriksa
      apakah bit LSB-nya 1 (jika ya, XOR dengan polynomial 0xA001)

    Args:
        data: bytes yang akan dihitung CRC-nya (TIDAK termasuk 2 byte CRC itu sendiri)

    Returns:
        int: Nilai CRC 16-bit
    """
    crc = 0xFFFF
    for byte in data:
        crc ^= byte                   # XOR byte masuk ke CRC
        for _ in range(8):            # Proses 8 bit
            if crc & 0x0001:          # Jika bit paling kanan = 1
                crc >>= 1
                crc ^= 0xA001         # XOR dengan polynomial Modbus
            else:
                crc >>= 1
    return crc


def verify_crc(frame: bytes) -> bool:
    """
    Verifikasi CRC dari sebuah frame Modbus RTU.

    Dalam frame Modbus RTU, 2 byte terakhir adalah CRC (Low byte dulu, lalu High byte).
    Kita hitung ulang CRC dari semua byte KECUALI 2 byte terakhir,
    lalu bandingkan hasilnya.

    Args:
        frame: Seluruh frame bytes termasuk 2 byte CRC di akhir

    Returns:
        bool: True jika CRC valid, False jika corrupt
    """
    if len(frame) < MODBUS_MIN_FRAME_LEN:
        return False

    # Pisahkan data dan CRC yang diterima
    data_without_crc = frame[:-2]
    received_crc_low  = frame[-2]   # Byte CRC ke-1 (Low byte)
    received_crc_high = frame[-1]   # Byte CRC ke-2 (High byte)

    # Rekonstruksi nilai CRC yang diterima (Little Endian: Low + High)
    received_crc = received_crc_low | (received_crc_high << 8)

    # Hitung CRC dari data yang diterima
    calculated_crc = _crc16_modbus(data_without_crc)

    return calculated_crc == received_crc


# ============================================================
# FUNGSI PARSING UTAMA
# ============================================================

def parse_modbus_response(raw_bytes: bytes) -> dict | None:
    """
    Mem-parsing frame Modbus RTU mentah menjadi dict nilai sensor.

    Fungsi ini adalah inti dari proses decoding. Alur kerjanya:

    1. Validasi panjang minimum frame (harus >= 5 byte agar tidak error)
    2. Cek Function Code: harus 0x03 (Read Holding Registers)
       - Jika 0x83 atau >= 0x80, sensor mengirim error code → tolak
    3. Baca Byte Count dari frame, tentukan panjang frame yang diharapkan
    4. Cek apakah frame sudah lengkap (belum terpotong)
    5. Verifikasi CRC untuk memastikan data tidak corrupt di perjalanan
    6. Unpack setiap register (2 byte, Big Endian unsigned short)
    7. Terapkan scaling:
       - Kelembapan: raw ÷ 10 (misal 245 → 24.5%)
       - Suhu:       raw ÷ 10 (misal 256 → 25.6°C)
       - pH:         raw ÷ 10 (misal 68  → 6.8)
       - EC, N, P, K: nilai langsung (integer, tanpa scaling)

    Args:
        raw_bytes: Bytes mentah dari socket TCP (satu frame Modbus RTU)

    Returns:
        dict dengan 7 key sensor, atau None jika parsing gagal.
        Format output:
        {
            'kelembapan_tanah': float,  # persen (%)
            'suhu': float,              # derajat Celsius
            'konduktivitas': float,     # µS/cm (EC)
            'ph_tanah': float,          # nilai pH
            'nitrogen': float,          # mg/kg
            'fosfor': float,            # mg/kg
            'kalium': float             # mg/kg
        }
    """

    # --- LANGKAH 1: Validasi panjang minimum ---
    # Tidak bisa membaca bahkan header jika kurang dari 5 byte
    if len(raw_bytes) < MODBUS_MIN_FRAME_LEN:
        logger.debug(f"[PARSER] Frame terlalu pendek: {len(raw_bytes)} byte (min {MODBUS_MIN_FRAME_LEN})")
        return None

    # --- LANGKAH 2: Cek Function Code ---
    func_code = raw_bytes[IDX_FUNC_CODE]
    if func_code >= 0x80:
        # Bit 7 = 1 berarti sensor merespons dengan Exception Code (error)
        error_code = raw_bytes[2] if len(raw_bytes) > 2 else 'N/A'
        logger.warning(f"[PARSER] Sensor mengirim Exception! FC=0x{func_code:02X}, ErrCode={error_code}")
        return None

    if func_code != 0x03:
        logger.warning(f"[PARSER] Function Code tidak dikenal: 0x{func_code:02X} (harus 0x03)")
        return None

    # --- LANGKAH 3: Baca Byte Count ---
    byte_count = raw_bytes[IDX_BYTE_COUNT]
    # Panjang total frame = header (3) + data (byte_count) + CRC (2)
    expected_len = IDX_DATA_START + byte_count + 2

    # --- LANGKAH 4: Cek kelengkapan frame ---
    if len(raw_bytes) < expected_len:
        logger.debug(
            f"[PARSER] Frame belum lengkap: dapat {len(raw_bytes)} byte, "
            f"butuh {expected_len} byte. Tunggu data berikutnya."
        )
        return None  # TCP bisa mengirim data terpotong, kembalikan None dan buffer

    # Ambil tepat satu frame (jika ada sisa, abaikan untuk sekarang)
    frame = raw_bytes[:expected_len]

    # --- LANGKAH 5: Verifikasi CRC ---
    if not verify_crc(frame):
        logger.warning(
            f"[PARSER] CRC GAGAL! Data mungkin corrupt. "
            f"Raw: {frame.hex()}"
        )
        return None

    # --- LANGKAH 6: Unpack Register ---
    # Data register dimulai dari byte ke-3 (setelah Slave ID, FC, Byte Count)
    # Format '>H' = Big Endian unsigned short (2 byte, 0–65535)
    data_payload = frame[IDX_DATA_START : IDX_DATA_START + byte_count]

    n_regs_received = byte_count // 2
    if n_regs_received < N_REGISTERS:
        logger.warning(
            f"[PARSER] Jumlah register tidak cukup: {n_regs_received}, "
            f"butuh {N_REGISTERS}"
        )
        return None

    # Unpack semua register sekaligus: '>8H' = 8 × Big Endian unsigned short
    try:
        regs = struct.unpack(f'>8H', data_payload[:N_REGISTERS * 2])
    except struct.error as e:
        logger.error(f"[PARSER] Gagal unpack register: {e}")
        return None

    # --- LANGKAH 7: Terapkan Scaling ---
    # reg[0] = Kelembapan   → ÷ 10
    # reg[1] = Suhu         → ÷ 10
    # reg[2] = EC (Konduktivitas) → langsung (integer µS/cm)
    # reg[3] = pH           → ÷ 10
    # reg[4] = Nitrogen N   → langsung (integer mg/kg)
    # reg[5] = Fosfor P     → langsung (integer mg/kg)
    # reg[6] = Kalium K     → langsung (integer mg/kg)
    # reg[7] = Salinitas    → langsung

    sensor_data = {
        'kelembapan_tanah': round(regs[0] / 10.0, 1),   # % kelembapan
        'suhu':             round(regs[1] / 10.0, 1),   # °C
        'konduktivitas':    float(regs[2]),               # µS/cm
        'ph_tanah':         round(regs[3] / 10.0, 1),   # pH
        'nitrogen':         float(regs[4]),               # mg/kg
        'fosfor':           float(regs[5]),               # mg/kg
        'kalium':           float(regs[6]),               # mg/kg
        'salinity':         float(regs[7]),               # dS/m atau mg/L
    }

    logger.debug(f"[PARSER] Parsing sukses: {sensor_data}")
    return sensor_data


# ============================================================
# BUFFER HANDLER
# ============================================================

class ModbusBufferHandler:
    """
    Menangani akumulasi bytes TCP yang mungkin datang terpotong-potong.

    Masalah umum pada TCP: Data bisa tiba dalam potongan-potongan kecil
    (TCP fragmentation), bukan satu frame utuh sekaligus. Kelas ini
    mengakumulasi buffer dan mencoba mem-parsing setiap kali ada data baru.

    Penggunaan:
        handler = ModbusBufferHandler()
        ...
        # Di dalam loop recv:
        chunk = conn.recv(1024)
        handler.feed(chunk)
        result = handler.try_parse()
        if result:
            # Proses sensor_data
    """

    def __init__(self):
        self._buffer = bytearray()

    def feed(self, data: bytes) -> None:
        """Tambahkan bytes baru ke buffer."""
        self._buffer.extend(data)

    def try_parse(self) -> dict | None:
        """
        Coba parsing frame dari buffer yang ada.
        Mendukung dua format:
        - Modbus RTU  (19 byte): [SlaveID][FC][ByteCount][Data×14][CRC×2]
        - Modbus TCP  (23 byte): [TransID×2][ProtoID×2=0000][Len×2][SlaveID][FC][ByteCount][Data×14]

        Returns:
            dict sensor_data jika berhasil, atau None
        """
        if len(self._buffer) < MODBUS_MIN_FRAME_LEN:
            return None

        # ── Deteksi Modbus TCP (MBAP header: ProtoID = 0x0000 di byte 2-3) ──
        if len(self._buffer) >= 6 and self._buffer[2] == 0x00 and self._buffer[3] == 0x00:
            mbap_len = 6  # Panjang MBAP header
            # Baca field Length dari MBAP (byte 4-5, Big Endian)
            pdu_with_unit = (self._buffer[4] << 8) | self._buffer[5]
            total_expected = mbap_len + pdu_with_unit  # header + (UnitID + FC + ByteCount + Data)

            if len(self._buffer) < total_expected:
                logger.debug(
                    f"[BUFFER] Modbus TCP belum lengkap: {len(self._buffer)}/{total_expected} byte"
                )
                return None

            # Ambil PDU (tanpa MBAP header, tanpa CRC karena TCP tidak pakai CRC)
            pdu = bytes(self._buffer[mbap_len:total_expected])
            logger.debug(f"[BUFFER] Modbus TCP response, PDU: {pdu.hex()}")

            # Buat frame RTU semu dengan CRC dummy agar parser bisa jalan
            # Parser akan verifikasi FC dan ByteCount, CRC di-bypass
            if len(pdu) >= 3:
                # Tambahkan CRC yang benar agar verify_crc lolos
                crc = _crc16_modbus(pdu)
                rtu_frame = pdu + bytes([crc & 0xFF, (crc >> 8) & 0xFF])
                result = parse_modbus_response(rtu_frame)
            else:
                result = None

            if result is not None:
                del self._buffer[:total_expected]
                logger.debug(f"[BUFFER] Modbus TCP frame dikonsumsi ({total_expected} byte)")
            return result

        # ── Modbus RTU biasa: cari [0x01][0x03] ──
        start_idx = -1
        for i in range(len(self._buffer) - 1):
            if self._buffer[i] == 0x01 and self._buffer[i+1] == 0x03:
                start_idx = i
                break

        if start_idx == -1:
            if len(self._buffer) > 64:
                logger.debug("[BUFFER] Tidak ada frame valid, membersihkan buffer")
                self._buffer.clear()
            return None

        if start_idx > 0:
            logger.debug(f"[BUFFER] Membuang {start_idx} byte noise sebelum frame")
            del self._buffer[:start_idx]

        result = parse_modbus_response(bytes(self._buffer))

        if result is not None:
            byte_count = self._buffer[IDX_BYTE_COUNT] if len(self._buffer) > IDX_BYTE_COUNT else 0
            consumed = IDX_DATA_START + byte_count + 2
            del self._buffer[:consumed]
            logger.debug(f"[BUFFER] RTU frame dikonsumsi, sisa buffer: {len(self._buffer)} byte")

        return result

    def clear(self) -> None:
        """Reset buffer (panggil saat koneksi terputus)."""
        self._buffer.clear()

    @property
    def buffer_size(self) -> int:
        return len(self._buffer)
