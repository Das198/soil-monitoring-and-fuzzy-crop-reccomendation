"""
Database Handler - Menyimpan dan mengambil data sensor dari database
"""

import mysql.connector
from typing import List, Dict, Optional
from datetime import datetime
from src.config import DB_HOST, DB_USER, DB_PASSWORD, DB_NAME, DB_CHARSET
from src.utils.logger import get_logger

logger = get_logger(__name__)


class DatabaseHandler:
    """Handler untuk operasi database MySQL"""
    
    def __init__(self, host: str = DB_HOST, user: str = DB_USER, 
                 password: str = DB_PASSWORD, database: str = DB_NAME):
        """
        Inisialisasi database handler
        
        Args:
            host: MySQL host
            user: MySQL user
            password: MySQL password
            database: Database name
        """
        self.host = host
        self.user = user
        self.password = password
        self.database = database
        self.connection = None
        self.is_connected = False
    
    def connect(self) -> bool:
        """
        Hubungkan ke database MySQL
        
        Returns:
            bool: True jika berhasil, False jika gagal
        """
        try:
            self.connection = mysql.connector.connect(
                host=self.host,
                user=self.user,
                password=self.password,
                database=self.database,
                charset=DB_CHARSET,
                autocommit=True
            )
            self.is_connected = True
            logger.info(f"[OK] Terkoneksi ke database {self.database}")
            return True
        except mysql.connector.Error as e:
            logger.error(f"[ERROR] Gagal terhubung ke database: {e}")
            self.is_connected = False
            return False
    
    def disconnect(self) -> None:
        """Putus koneksi dari database"""
        if self.connection and self.is_connected:
            self.connection.close()
            self.is_connected = False
            logger.info("[OK] Koneksi database ditutup")
    
    def save_sensor_data(
        self,
        slave_id: int,
        timestamp: datetime,
        sensor_data: Dict
    ) -> bool:
        """
        Simpan data sensor ke database
        
        Args:
            slave_id: Slave ID sensor
            timestamp: Timestamp pembacaan
            sensor_data: Dictionary data sensor
            
        Returns:
            bool: True jika berhasil, False jika gagal
        """
        if not self.is_connected:
            logger.warning("Database tidak terkoneksi")
            return False
        
        try:
            cursor = self.connection.cursor()
            
            query = """
                INSERT INTO sensor_data 
                (slave_id, timestamp, kelembapan_tanah, suhu, konduktivitas, 
                 ph_tanah, nitrogen, fosfor, kalium, salinity)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            values = (
                slave_id,
                timestamp,
                sensor_data.get('kelembapan_tanah'),
                sensor_data.get('suhu'),
                sensor_data.get('konduktivitas'),
                sensor_data.get('ph_tanah'),
                sensor_data.get('nitrogen'),
                sensor_data.get('fosfor'),
                sensor_data.get('kalium'),
                sensor_data.get('salinity')
            )
            
            cursor.execute(query, values)
            logger.debug(f"[OK] Data sensor ID {slave_id} disimpan")
            cursor.close()
            return True
            
        except mysql.connector.Error as e:
            logger.error(f"[ERROR] Error menyimpan data: {e}")
            return False
    
    def get_recent_data(
        self,
        slave_ids: List[int] = None,
        limit: int = 1
    ) -> Optional[List[Dict]]:
        """
        Ambil data sensor terbaru dari kumpulan slaves dan hitung rata-ratanya
        
        Args:
            slave_ids: List slave ID yang aktif
            limit: Record per slave (biasanya 1 saja)
            
        Returns:
            List[Dict]: Array yang berisi satu elemen Dict berupa nilai rata-rata, atau None jika tidak ada data sama sekali.
        """
        if not self.is_connected:
            logger.warning("Database tidak terkoneksi")
            return None
        
        try:
            cursor = self.connection.cursor(dictionary=True)
            
            if not slave_ids:
                slave_ids = [2] # Fallback
            
            all_results = []
            
            # Tarik data untuk tiap slave yang aktif
            for sid in slave_ids:
                try:
                    query = f"SELECT * FROM slave_{sid} ORDER BY timestamp DESC LIMIT {limit}"
                    cursor.execute(query)
                    rows = cursor.fetchall()
                    if rows:
                        all_results.extend(rows)
                except mysql.connector.Error as e:
                    logger.warning(f"[DB] Gagal menarik data slave_{sid}: {e}")
            
            cursor.close()
            
            if not all_results:
                return []
                
            # Rata-ratakan hasil dari semua slaves
            count = len(all_results)
            avg_row = {
                'slave_id': 0, # Penanda kombinasi rata-rata
                'timestamp': all_results[0].get('timestamp'),
                'kelembapan_tanah': sum(row.get('kelembapan', 0.0) or 0.0 for row in all_results) / count,
                'ph_tanah': sum(row.get('ph', 0.0) or 0.0 for row in all_results) / count,
                'suhu': sum(row.get('suhu', 0.0) or 0.0 for row in all_results) / count,
                'konduktivitas': sum(row.get('konduktivitas', 0.0) or 0.0 for row in all_results) / count,
                'nitrogen': sum(row.get('nitrogen', 0.0) or 0.0 for row in all_results) / count,
                'fosfor': sum(row.get('fosfor', 0.0) or 0.0 for row in all_results) / count,
                'kalium': sum(row.get('kalium', 0.0) or 0.0 for row in all_results) / count,
                'salinity': sum(row.get('salinity', 0.0) or 0.0 for row in all_results) / count
            }
            
            return [avg_row]
            
        except mysql.connector.Error as e:
            logger.error(f"✗ Error mengambil data: {e}")
            return None
    
    def create_tables(self) -> bool:
        """
        Buat tabel database jika belum ada
        
        Returns:
            bool: True jika berhasil, False jika gagal
        """
        if not self.is_connected:
            return False
        
        try:
            cursor = self.connection.cursor()
            
            # Tabel sensor_data
            create_table_query = """
                CREATE TABLE IF NOT EXISTS sensor_data (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    slave_id INT NOT NULL,
                    timestamp DATETIME NOT NULL,
                    kelembapan_tanah FLOAT,
                    suhu FLOAT,
                    konduktivitas FLOAT,
                    ph_tanah FLOAT,
                    nitrogen FLOAT,
                    fosfor FLOAT,
                    kalium FLOAT,
                    salinity FLOAT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_slave_time (slave_id, timestamp)
                )
            """
            
            cursor.execute(create_table_query)
            logger.info("[OK] Tabel sensor_data dibuat/sudah ada")
            cursor.close()
            return True
            
        except mysql.connector.Error as e:
            logger.error(f"[ERROR] Error membuat tabel: {e}")
            return False


def main():
    """Test database handler"""
    db = DatabaseHandler()
    
    if db.connect():
        if db.create_tables():
            # Test insert
            test_data = {
                'kelembapan_tanah': 50.5,
                'suhu': 25.0,
                'konduktivitas': 2.5,
                'ph_tanah': 6.8,
                'nitrogen': 100,
                'fosfor': 30,
                'kalium': 100,
                'salinity': 1.0
            }
            
            if db.save_sensor_data(1, datetime.now(), test_data):
                logger.info("✓ Test data berhasil disimpan")
            
            # Test retrieve
            results = db.get_recent_data(limit=5)
            if results:
                logger.info(f"✓ Retrieved {len(results)} records")
            
        db.disconnect()


if __name__ == "__main__":
    main()
