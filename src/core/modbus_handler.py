"""
Modbus Handler - Mengelola koneksi dan komunikasi Modbus TCP
"""

from pyModbusTCP.client import ModbusClient
import time
from typing import Optional, List
from src.utils.logger import get_logger

logger = get_logger(__name__)


class ModbusHandler:
    """Handler untuk komunikasi Modbus TCP dengan sensor"""
    
    def __init__(self, host: str, port: int, timeout: float = 5.0):
        """
        Inisialisasi Modbus Handler
        
        Args:
            host: IP Address Modbus server
            port: Port Modbus server
            timeout: Timeout koneksi dalam detik
        """
        self.host = host
        self.port = port
        self.timeout = timeout
        self.client = ModbusClient(
            host=host,
            port=port,
            auto_open=True,
            auto_close=False,
            timeout=timeout
        )
        self.is_connected = False
    
    def connect(self) -> bool:
        """
        Buka koneksi Modbus
        
        Returns:
            bool: True jika berhasil, False jika gagal
        """
        try:
            if self.client.open():
                self.is_connected = True
                logger.info(f"[OK] Koneksi Modbus ke {self.host}:{self.port} berhasil")
                return True
            else:
                logger.error(f"[ERROR] Gagal membuka koneksi Modbus ke {self.host}:{self.port}")
                return False
        except Exception as e:
            logger.error(f"[ERROR] Error saat membuka koneksi: {e}")
            return False
    
    def disconnect(self) -> None:
        """Tutup koneksi Modbus"""
        if self.is_connected and self.client.is_open:
            self.client.close()
            self.is_connected = False
            logger.info("[OK] Koneksi Modbus ditutup")
    
    def is_open(self) -> bool:
        """Cek apakah koneksi masih terbuka"""
        return self.client.is_open
    
    def read_registers(
        self, 
        unit_id: int,
        start_address: int,
        register_count: int
    ) -> Optional[List[int]]:
        """
        Baca holding registers
        
        Args:
            unit_id: Slave ID
            start_address: Alamat register awal
            register_count: Jumlah register yang dibaca
            
        Returns:
            List[int]: Nilai register atau None jika gagal
        """
        try:
            self.client.unit_id = unit_id
            registers = self.client.read_holding_registers(start_address, register_count)
            
            if registers:
                logger.debug(f"[ID {unit_id}] [OK] Membaca {register_count} register dari alamat {start_address}")
                return registers
            else:
                logger.warning(f"[ID {unit_id}] [FAILED] Gagal membaca register")
                # Coba reconnect
                if not self.is_open():
                    logger.info(f"[ID {unit_id}] Mencoba reconnect...")
                    self.connect()
                return None
                
        except Exception as e:
            logger.error(f"[ID {unit_id}] Error saat membaca register: {e}")
            return None
    
    def write_register(
        self,
        unit_id: int,
        register_address: int,
        value: int
    ) -> bool:
        """
        Tulis single register
        
        Args:
            unit_id: Slave ID
            register_address: Alamat register
            value: Nilai yang akan ditulis
            
        Returns:
            bool: True jika berhasil, False jika gagal
        """
        try:
            self.client.unit_id = unit_id
            result = self.client.write_single_register(register_address, value)
            
            if result:
                logger.info(f"[ID {unit_id}] [OK] Menulis register {register_address} = {value}")
                return True
            else:
                logger.error(f"[ID {unit_id}] [ERROR] Gagal menulis register {register_address}")
                return False
                
        except Exception as e:
            logger.error(f"[ID {unit_id}] Error saat menulis register: {e}")
            return False
