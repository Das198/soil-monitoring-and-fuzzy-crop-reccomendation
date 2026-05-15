"""
database_vps.py
===============
Database handler untuk VPS menggunakan pymysql.
Menyimpan data sensor dan hasil rekomendasi fuzzy ke MariaDB/MySQL.

Skema tabel yang digunakan (sesuai tanah_db.sql):
- slave_1 (kelembapan, suhu, ph, nitrogen, fosfor, kalium, salinity)
- slave_2 (kolom sama)
- slave_3 (kolom sama)

Kelas ini secara otomatis membuat database dan tabel jika belum ada.
"""

import pymysql
import pymysql.cursors
import logging
from datetime import datetime
from typing import Optional, List, Dict

logger = logging.getLogger(__name__)


class DatabaseVPS:
    """
    Handler database MySQL/MariaDB untuk server VPS.
    Menggunakan pymysql dengan auto-reconnect.
    """

    def __init__(
        self,
        host: str = "localhost",
        user: str = "root",
        password: str = "",
        database: str = "tanah_db",
        port: int = 3306,
        charset: str = "utf8mb4"
    ):
        self.host     = host
        self.user     = user
        self.password = password
        self.database = database
        self.port     = port
        self.charset  = charset
        self._conn: Optional[pymysql.connections.Connection] = None

    # ------------------------------------------------------------------
    # KONEKSI
    # ------------------------------------------------------------------

    def connect(self) -> bool:
        """Buka koneksi ke database, buat DB & tabel jika belum ada."""
        try:
            # Pertama: konek TANPA memilih database dulu (untuk bisa membuat DB)
            self._conn = pymysql.connect(
                host=self.host,
                user=self.user,
                password=self.password,
                port=self.port,
                charset=self.charset,
                autocommit=True,
                connect_timeout=10
            )
            self._ensure_database_exists()
            self._conn.close() # Tutup koneksi awal

            # Kedua: Konek ulang DENGAN parameter database
            # Ini sangat penting agar jika koneksi terputus dan pymysql melakukan auto-reconnect,
            # ia akan tetap mengingat database apa yang sedang digunakan.
            self._conn = pymysql.connect(
                host=self.host,
                user=self.user,
                password=self.password,
                database=self.database,
                port=self.port,
                charset=self.charset,
                autocommit=True,
                connect_timeout=10
            )
            
            self._create_tables()
            logger.info(f"[DB] Terhubung ke database '{self.database}' di {self.host}")
            return True
        except pymysql.Error as e:
            logger.error(f"[DB] Gagal terhubung: {e}")
            self._conn = None
            return False

    def _ensure_database_exists(self) -> None:
        """Buat database jika belum ada."""
        with self._conn.cursor() as cur:
            cur.execute(
                f"CREATE DATABASE IF NOT EXISTS `{self.database}` "
                f"CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci"
            )
        logger.info(f"[DB] Database '{self.database}' siap.")

    def _select_database(self) -> None:
        """Pilih database aktif."""
        self._conn.select_db(self.database)

    def _create_tables(self) -> None:
        """Buat tabel slave_1, slave_2, slave_3, dan rekomendasi jika belum ada."""
        slave_ddl = """
            CREATE TABLE IF NOT EXISTS `{table}` (
                `id`         INT(11)   NOT NULL AUTO_INCREMENT,
                `timestamp`  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                             ON UPDATE CURRENT_TIMESTAMP,
                `kelembapan` FLOAT     NOT NULL DEFAULT 0,
                `suhu`       FLOAT     NOT NULL DEFAULT 0,
                `ph`         FLOAT     NOT NULL DEFAULT 0,
                `nitrogen`   FLOAT     NOT NULL DEFAULT 0,
                `fosfor`     FLOAT     NOT NULL DEFAULT 0,
                `kalium`     FLOAT     NOT NULL DEFAULT 0,
                `salinity`   FLOAT     NOT NULL DEFAULT 0,
                PRIMARY KEY (`id`)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
        """
        rekomendasi_ddl = """
            CREATE TABLE IF NOT EXISTS `rekomendasi` (
                `id`         INT(11)      NOT NULL AUTO_INCREMENT,
                `slave_id`   TINYINT(4)   NOT NULL DEFAULT 1,
                `timestamp`  DATETIME     NOT NULL,
                `tanaman_1`  VARCHAR(50)  DEFAULT NULL,
                `skor_1`     FLOAT        DEFAULT NULL,
                `tanaman_2`  VARCHAR(50)  DEFAULT NULL,
                `skor_2`     FLOAT        DEFAULT NULL,
                `tanaman_3`  VARCHAR(50)  DEFAULT NULL,
                `skor_3`     FLOAT        DEFAULT NULL,
                `tanaman_4`  VARCHAR(50)  DEFAULT NULL,
                `skor_4`     FLOAT        DEFAULT NULL,
                `tanaman_5`  VARCHAR(50)  DEFAULT NULL,
                `skor_5`     FLOAT        DEFAULT NULL,
                `data_json`  TEXT         DEFAULT NULL,
                PRIMARY KEY (`id`)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
        """
        with self._conn.cursor() as cur:
            for slave_num in [1, 2, 3]:
                cur.execute(slave_ddl.format(table=f"slave_{slave_num}"))
            cur.execute(rekomendasi_ddl)
        self._migrate_rekomendasi_table()
        logger.info("[DB] Semua tabel siap (slave_1, slave_2, slave_3, rekomendasi).")

    def _migrate_rekomendasi_table(self) -> None:
        """Tambahkan kolom data_json ke tabel rekomendasi jika belum ada."""
        try:
            with self._conn.cursor() as cur:
                cur.execute("SHOW COLUMNS FROM `rekomendasi` LIKE 'data_json'")
                if cur.fetchone() is None:
                    cur.execute(
                        "ALTER TABLE `rekomendasi` ADD COLUMN `data_json` TEXT DEFAULT NULL"
                    )
                    logger.info("[DB] Kolom data_json ditambahkan ke tabel rekomendasi.")
        except Exception as e:
            logger.warning(f"[DB] Migrasi rekomendasi: {e}")


    def disconnect(self) -> None:
        """Tutup koneksi database."""
        if self._conn:
            try:
                self._conn.close()
            except Exception:
                pass
            self._conn = None
            logger.info("[DB] Koneksi database ditutup.")

    def _ensure_connected(self) -> bool:
        """
        Cek koneksi, lakukan reconnect jika terputus (auto-reconnect).
        Returns True jika koneksi aktif.
        """
        if self._conn is None:
            return self.connect()
        try:
            self._conn.ping(reconnect=True)
            return True
        except pymysql.Error:
            logger.warning("[DB] Koneksi terputus, mencoba reconnect...")
            return self.connect()

    @property
    def is_connected(self) -> bool:
        """Cek status koneksi tanpa auto-reconnect."""
        if self._conn is None:
            return False
        try:
            self._conn.ping(reconnect=False)
            return True
        except Exception:
            return False

    # ------------------------------------------------------------------
    # SIMPAN DATA SENSOR
    # ------------------------------------------------------------------

    def save_reading(
        self,
        sensor_data: Dict,
        slave_id: int = 1,
        timestamp: Optional[datetime] = None
    ) -> bool:
        """
        Simpan satu baris data sensor ke tabel slave_<slave_id>.

        Args:
            sensor_data: Dict hasil parsing Modbus (key: kelembapan_tanah, suhu, dll.)
            slave_id:    Nomor slave (1, 2, atau 3). Default: 1
            timestamp:   Waktu pembacaan. Default: sekarang.

        Returns:
            True jika berhasil, False jika gagal.
        """
        if not self._ensure_connected():
            return False

        table = f"slave_{slave_id}"
        ts = timestamp or datetime.now()

        sql = f"""
            INSERT INTO `{table}`
                (timestamp, kelembapan, suhu, ph, nitrogen, fosfor, kalium, salinity)
            VALUES
                (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        values = (
            ts,
            sensor_data.get('kelembapan_tanah', 0),
            sensor_data.get('suhu', 0),
            sensor_data.get('ph_tanah', 0),
            sensor_data.get('nitrogen', 0),
            sensor_data.get('fosfor', 0),
            sensor_data.get('kalium', 0),
            # salinity tidak ada di sensor 7-in-1 (hanya 7 reg), defaultkan 0
            sensor_data.get('salinity', 0),
        )

        try:
            with self._conn.cursor() as cur:
                cur.execute(sql, values)
            logger.debug(f"[DB] Data sensor slave_{slave_id} tersimpan ({ts})")
            return True
        except pymysql.Error as e:
            logger.error(f"[DB] Gagal INSERT ke {table}: {e}")
            return False

    # ------------------------------------------------------------------
    # SIMPAN HASIL REKOMENDASI FUZZY
    # ------------------------------------------------------------------

    def save_recommendation(
        self,
        results: List[Dict],
        slave_id: int = 1,
        timestamp: Optional[datetime] = None
    ) -> bool:
        """
        Simpan Top-5 hasil rekomendasi fuzzy ke tabel 'rekomendasi'.

        Args:
            results:   List[Dict] dari fuzzy.get_all_crop_recommendations(),
                       sudah diurutkan dari skor tertinggi.
                       Format setiap item: {'nama': str, 'skor': float, ...}
            slave_id:  Nomor slave
            timestamp: Waktu evaluasi. Default: sekarang.

        Returns:
            True jika berhasil, False jika gagal.
        """
        if not self._ensure_connected():
            return False
        if not results:
            return False

        import json as _json

        ts = timestamp or datetime.now()
        top5 = results[:5]  # Ambil maksimal 5 teratas untuk kolom bernama

        # Siapkan nilai kolom Top-5
        vals = []
        for i in range(5):
            if i < len(top5):
                vals.append(top5[i].get('nama', None))
                vals.append(round(top5[i].get('skor', 0), 2))
            else:
                vals.append(None)
                vals.append(None)

        # Simpan semua hasil (22 tanaman) sebagai JSON
        # Hapus 'details' yang terlalu besar jika tidak diperlukan, atau simpan semua
        try:
            data_json = _json.dumps(results, ensure_ascii=False, default=str)
        except Exception:
            data_json = None

        sql = """
            INSERT INTO `rekomendasi`
                (slave_id, timestamp,
                 tanaman_1, skor_1,
                 tanaman_2, skor_2,
                 tanaman_3, skor_3,
                 tanaman_4, skor_4,
                 tanaman_5, skor_5,
                 data_json)
            VALUES
                (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        try:
            with self._conn.cursor() as cur:
                cur.execute(sql, [slave_id, ts] + vals + [data_json])
            logger.info(
                f"[DB] Rekomendasi disimpan ({len(results)} tanaman): "
                f"{', '.join(str(v) for v in vals[::2] if v)}"
            )
            return True
        except pymysql.Error as e:
            logger.error(f"[DB] Gagal INSERT rekomendasi: {e}")
            return False


    # ------------------------------------------------------------------
    # AMBIL DATA TERBARU (untuk fuzzy evaluasi)
    # ------------------------------------------------------------------

    def get_recent_data(
        self,
        slave_ids: List[int] = None,
        limit: int = 1
    ) -> Optional[List[Dict]]:
        """
        Ambil data terbaru dari slave yang aktif, kembalikan rata-ratanya.

        Args:
            slave_ids: List slave ID yang aktif. Default: [1]
            limit:     Jumlah record per slave. Default: 1

        Returns:
            List berisi satu Dict rata-rata, atau None jika error.
        """
        if not self._ensure_connected():
            return None

        slave_ids = slave_ids or [1]
        all_rows = []

        try:
            with self._conn.cursor(pymysql.cursors.DictCursor) as cur:
                for sid in slave_ids:
                    table = f"slave_{sid}"
                    try:
                        cur.execute(
                            f"SELECT * FROM `{table}` ORDER BY timestamp DESC LIMIT %s",
                            (limit,)
                        )
                        rows = cur.fetchall()
                        all_rows.extend(rows)
                    except pymysql.Error as e:
                        logger.warning(f"[DB] Gagal baca {table}: {e}")

            if not all_rows:
                return []

            count = len(all_rows)
            avg = {
                'slave_id':        0,
                'timestamp':       all_rows[0].get('timestamp'),
                'kelembapan_tanah': sum(r.get('kelembapan', 0) or 0 for r in all_rows) / count,
                'suhu':            sum(r.get('suhu', 0) or 0 for r in all_rows) / count,
                'ph_tanah':        sum(r.get('ph', 0) or 0 for r in all_rows) / count,
                'konduktivitas':   0,  # Tidak ada di tabel baru
                'nitrogen':        sum(r.get('nitrogen', 0) or 0 for r in all_rows) / count,
                'fosfor':          sum(r.get('fosfor', 0) or 0 for r in all_rows) / count,
                'kalium':          sum(r.get('kalium', 0) or 0 for r in all_rows) / count,
                'salinity':        sum(r.get('salinity', 0) or 0 for r in all_rows) / count,
            }
            return [avg]

        except pymysql.Error as e:
            logger.error(f"[DB] Error mengambil data: {e}")
            return None
