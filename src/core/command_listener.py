"""
Command Listener - Mendengarkan perintah dari eksternal (Node-RED)
"""

import socket
import threading
from typing import Callable, Optional
from src.utils.logger import get_logger

logger = get_logger(__name__)


class CommandListener:
    """TCP Server sederhana untuk menerima instruksi secara asinkron dari Node-RED"""
    
    def __init__(self, host: str, port: int, callback: Callable[[str], None]):
        """
        Inisialisasi Command Listener
        
        Args:
            host: IP address untuk listen (biasanya 127.0.0.1 atau 0.0.0.0)
            port: Port TCP
            callback: Fungsi yang dipanggil saat ada pesan (teks murni)
        """
        self.host = host
        self.port = port
        self.callback = callback
        self.server_socket: Optional[socket.socket] = None
        self.is_running = False
        self.listen_thread: Optional[threading.Thread] = None
        
    def start(self) -> bool:
        """
        Mulai mendengarkan di thread terpisah.
        
        Returns:
            bool: True jika berhasil binding dan start, False jika gagal.
        """
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            self.server_socket.settimeout(1.0) # Agar loop tidak terperangkap blokir
            
            self.is_running = True
            
            self.listen_thread = threading.Thread(target=self._listen_loop, daemon=True)
            self.listen_thread.start()
            
            logger.info(f"[OK] Command Listener berjalan di {self.host}:{self.port}")
            return True
        except Exception as e:
            logger.error(f"[ERROR] Gagal menjalankan Command Listener di port {self.port}: {e}")
            self.is_running = False
            return False

    def stop(self) -> None:
        """Berhentikan listener secara anggun."""
        self.is_running = False
        if self.listen_thread:
            self.listen_thread.join(timeout=2.0)
        
        if self.server_socket:
            try:
                self.server_socket.close()
            except Exception as e:
                logger.error(f"Error saat menutup Command Listener socket: {e}")
        logger.info("[OK] Command Listener dihentikan")

    def _listen_loop(self) -> None:
        """Loop internal dari TCP Server"""
        while self.is_running:
            try:
                client_sock, addr = self.server_socket.accept()
                client_sock.settimeout(1.0)
                with client_sock:
                    logger.info(f"[OK] Node-RED Control terhubung dari {addr}")
                    while self.is_running:
                        try:
                            # Membaca data singkat, asumsi plain text commands ("START", "STOP")
                            data = client_sock.recv(1024)
                            if not data:
                                break # Client terputus
                            
                            command_text = data.decode('utf-8').strip()
                            if command_text:
                                # Teruskan ke handler utama
                                self.callback(command_text)
                        except socket.timeout:
                            continue
                        except Exception as inner_e:
                            logger.error(f"[ERROR] Membaca command: {inner_e}")
                            break
            except socket.timeout:
                # Timeout wajar, loop dilanjutkan untuk cek is_running
                continue
            except Exception as e:
                if self.is_running:
                    logger.error(f"[ERROR] Command Listener connection error: {e}")
