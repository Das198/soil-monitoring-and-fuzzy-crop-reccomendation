"""
Main Entry Point - Sistem Monitoring Tanah Real-time
Mengintegrasikan Modbus, Node-RED, dan Sensor Data Processing
"""

import time
from datetime import datetime
from src.config import (
    MODBUS_SERVER_HOST,
    MODBUS_SERVER_PORT,
    MODBUS_TIMEOUT,
    MODBUS_SLAVE_IDS,
    REGISTER_START_ADDRESS,
    REGISTER_COUNT,
    POLLING_INTERVAL,
    INTER_SLAVE_DELAY,
    INTER_CYCLE_DELAY,
    NODE_RED_IP,
    NODE_RED_PORT,
    NODE_RED_TIMEOUT,
    COMMAND_SERVER_IP,
    COMMAND_SERVER_PORT
)
from src.core import ModbusHandler, SensorData, NodeREDSender, CommandListener
from src.utils.logger import get_logger

logger = get_logger(__name__)


class SoilMonitoringSystem:
    """Sistem monitoring tanah terintegrasi"""
    
    def __init__(self):
        """Inisialisasi sistem monitoring"""
        self.modbus = ModbusHandler(
            host=MODBUS_SERVER_HOST,
            port=MODBUS_SERVER_PORT,
            timeout=MODBUS_TIMEOUT
        )
        self.sensor_processor = SensorData()
        self.node_red = NodeREDSender(
            host=NODE_RED_IP,
            port=NODE_RED_PORT,
            timeout=NODE_RED_TIMEOUT
        )
        self.command_listener = CommandListener(
            host=COMMAND_SERVER_IP,
            port=COMMAND_SERVER_PORT,
            callback=self.handle_command
        )
        self.is_running = False
        self.is_monitoring = False
    
    def handle_command(self, cmd_str: str) -> None:
        """Handler untuk instruksi dari Node-RED"""
        cmd = cmd_str.strip().upper()
        if cmd == "START":
            if not self.is_monitoring:
                self.is_monitoring = True
                logger.info("[MODE] Beralih ke mode MONITORING. Siklus pembacaan dimulai.")
            else:
                logger.info("[MODE] Sudah dalam mode MONITORING.")
        elif cmd == "STOP":
            if self.is_monitoring:
                self.is_monitoring = False
                logger.info("[MODE] Beralih ke mode STANDBY. Proses dihentikan sementara.")
            else:
                logger.info("[MODE] Sudah dalam mode STANDBY.")
        elif cmd == "GENERATE":
            logger.info("[ACTION] Tombol GENERATE Ditekan! Placeholder untuk logic Machine Learning nantinya.")
        else:
            logger.warning(f"[WARN] Perintah tidak dikenal: {cmd_str}")
    
    def start(self) -> bool:
        """
        Mulai sistem monitoring
        
        Returns:
            bool: True jika berhasil, False jika gagal
        """
        logger.info("=" * 60)
        logger.info("[SYSTEM] SISTEM MONITORING TANAH - MEMULAI")
        logger.info("=" * 60)
        
        # Koneksikan ke Modbus
        if not self.modbus.connect():
            logger.error("[ERROR] Gagal terhubung ke Modbus Gateway")
            return False
        
        # Koneksikan ke Node-RED
        if not self.node_red.connect():
            logger.warning("[WARN] Gagal terhubung ke Node-RED (akan retry)")
            
        # Nyalakan Command Listener
        if not self.command_listener.start():
            logger.warning("[WARN] Gagal memulai Command Listener")
        
        self.is_running = True
        logger.info("[MODE] Sistem berada dalam mode STANDBY. Menunggu tombol START dari Node-RED.")
        return True
    
    def stop(self) -> None:
        """Hentikan sistem monitoring"""
        logger.info("=" * 60)
        logger.info("[STOP] SISTEM MONITORING TANAH - BERHENTI")
        logger.info("=" * 60)
        self.is_running = False
        self.is_monitoring = False
        self.command_listener.stop()
        self.modbus.disconnect()
        self.node_red.disconnect()
    
    def read_cycle(self) -> None:
        """Jalankan satu siklus pembacaan data dari semua slave"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        logger.info(f"\n[DATA] --- {timestamp} - Mulai Siklus Pembacaan ---")
        
        for unit_id in MODBUS_SLAVE_IDS:
            # 1. BACA DATA DARI MODBUS
            raw_registers = self.modbus.read_registers(
                unit_id=unit_id,
                start_address=REGISTER_START_ADDRESS,
                register_count=REGISTER_COUNT
            )
            
            if not raw_registers:
                logger.warning(f"[ID {unit_id}] [FAILED] Gagal membaca register")
                time.sleep(INTER_SLAVE_DELAY)
                continue
            
            # 2. PROSES DATA SENSOR (Mapping + Scaling)
            sensor_data = self.sensor_processor.process_registers(raw_registers)
            
            if sensor_data:
                # 3. TAMPILKAN DATA
                logger.info(f"[ID {unit_id}] [OK] SUKSES:")
                readable_output = self.sensor_processor.get_readable_output(sensor_data)
                logger.info(readable_output)
                
                # 4. KIRIM KE NODE-RED
                if self.node_red.is_connected:
                    if self.node_red.send_data(sensor_data, unit_id, timestamp):
                        logger.info(f"[ID {unit_id}] [OK] Data terkirim ke Node-RED")
                    else:
                        logger.warning(f"[ID {unit_id}] [WARN] Gagal mengirim ke Node-RED")
                else:
                    logger.debug(f"[ID {unit_id}] [SKIP] Node-RED tidak terkoneksi")
            
            time.sleep(INTER_SLAVE_DELAY)
    
    def run(self) -> None:
        """Loop utama monitoring"""
        try:
            if not self.start():
                return
            
            while self.is_running:
                try:
                    if self.is_monitoring:
                        self.read_cycle()
                        time.sleep(INTER_CYCLE_DELAY)
                    else:
                        # Dalam mode Standby, hindari penggunaan CPU berlebih
                        time.sleep(1)
                except KeyboardInterrupt:
                    logger.info("\n[STOP] Program dihentikan oleh pengguna (Ctrl+C)")
                    break
                except Exception as e:
                    logger.error(f"[ERROR] Error dalam siklus pembacaan: {e}")
                    time.sleep(1)
                    continue
        
        except Exception as e:
            logger.error(f"[ERROR] Fatal error: {e}")
        finally:
            self.stop()


def main():
    """Entry point aplikasi"""
    system = SoilMonitoringSystem()
    system.run()


if __name__ == "__main__":
    main()
