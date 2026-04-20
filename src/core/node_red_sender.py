"""
Node-RED Sender - Mengirim data sensor ke Node-RED via TCP
"""

import socket
import json
import time
from typing import Dict, Optional
from src.utils.logger import get_logger

logger = get_logger(__name__)


class NodeREDSender:
    """Pengirim data ke Node-RED via TCP socket"""
    
    def __init__(self, host: str, port: int, timeout: float = 5.0):
        """
        Inisialisasi Node-RED Sender
        
        Args:
            host: IP address Node-RED
            port: Port TCP Node-RED
            timeout: Timeout koneksi dalam detik
        """
        self.host = host
        self.port = port
        self.timeout = timeout
        self.socket = None
        self.is_connected = False
    
    def connect(self) -> bool:
        """
        Hubungkan ke Node-RED
        
        Returns:
            bool: True jika berhasil, False jika gagal
        """
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(self.timeout)
            self.socket.connect((self.host, self.port))
            self.is_connected = True
            logger.info(f"[OK] Terkoneksi ke Node-RED di {self.host}:{self.port}")
            return True
        except Exception as e:
            logger.error(f"[ERROR] Gagal terhubung ke Node-RED: {e}")
            self.is_connected = False
            return False
    
    def disconnect(self) -> None:
        """Putus koneksi dari Node-RED"""
        try:
            if self.socket:
                self.socket.close()
            self.is_connected = False
            logger.info("[OK] Koneksi Node-RED ditutup")
        except Exception as e:
            logger.error(f"Error saat menutup koneksi: {e}")
    
    def send_data(self, sensor_data: Dict, slave_id: int, timestamp: str) -> bool:
        """
        Kirim data sensor ke Node-RED
        
        Args:
            sensor_data: Dictionary data sensor
            slave_id: ID slave Modbus
            timestamp: Timestamp pembacaan
            
        Returns:
            bool: True jika berhasil, False jika gagal
        """
        try:
            if not self.is_connected:
                logger.warning("Tidak terkoneksi ke Node-RED, mencoba reconnect...")
                if not self.connect():
                    return False
            
            # Buat payload JSON
            payload = {
                "slave_id": slave_id,
                "timestamp": timestamp,
                "data": sensor_data
            }
            
            json_data = json.dumps(payload) + "\n"
            self.socket.sendall(json_data.encode("utf-8"))
            logger.debug(f"[OK] Data dari ID {slave_id} terkirim ke Node-RED")
            return True
            
        except socket.error as e:
            logger.error(f"[ERROR] Error saat mengirim ke Node-RED: {e}")
            self.is_connected = False
            return False
        except Exception as e:
            logger.error(f"[ERROR] Unexpected error: {e}")
            return False
    
    def send_batch(self, data_list: list) -> int:
        """
        Kirim multiple data dalam batch
        
        Args:
            data_list: List of dictionaries dengan keys: sensor_data, slave_id, timestamp
            
        Returns:
            int: Jumlah data yang berhasil dikirim
        """
        sent_count = 0
        for data in data_list:
            if self.send_data(
                sensor_data=data.get("sensor_data"),
                slave_id=data.get("slave_id"),
                timestamp=data.get("timestamp")
            ):
                sent_count += 1
            time.sleep(0.05)  # Small delay antar pengiriman
        
        return sent_count
    
    def is_alive(self) -> bool:
        """
        Cek apakah koneksi masih hidup (optional ping)
        
        Returns:
            bool: True jika koneksi aktif
        """
        if not self.is_connected:
            return False
        
        try:
            # Send empty keepalive
            self.socket.send(b"")
            return True
        except:
            self.is_connected = False
            return False
