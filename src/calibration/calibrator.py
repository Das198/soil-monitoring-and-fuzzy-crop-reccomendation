"""
Calibrator - Modul kalibrasi sensor pH CWT-SOIL
Merge dari kalibrasi.py dan kalibrasiBARU.py
"""

import time
from typing import Dict, Optional
from src.core import ModbusHandler
from src.config import (
    MODBUS_SERVER_HOST,
    MODBUS_SERVER_PORT,
    MODBUS_TIMEOUT,
    PH_CALIBRATION_REGISTER,
    PH_COMMAND_REGISTER,
    PH_COMMAND_SAVE,
    CALIBRATION_POINT
)
from src.utils.logger import get_logger

logger = get_logger(__name__)


class PHCalibrator:
    """Kalibrasi sensor pH CWT-SOIL"""
    
    def __init__(self):
        """Inisialisasi calibrator"""
        self.modbus = ModbusHandler(
            host=MODBUS_SERVER_HOST,
            port=MODBUS_SERVER_PORT,
            timeout=MODBUS_TIMEOUT
        )
        self.calibration_points = CALIBRATION_POINT
    
    def connect(self) -> bool:
        """Hubungkan ke Modbus Gateway"""
        return self.modbus.connect()
    
    def disconnect(self) -> None:
        """Putus koneksi dari Modbus Gateway"""
        self.modbus.disconnect()
    
    def calibrate_single_point(
        self,
        unit_id: int,
        buffer_name: str,
        scaled_value: int,
        use_command_register: bool = True
    ) -> bool:
        """
        Kalibrasi pada satu titik standar buffer
        
        Args:
            unit_id: Slave ID sensor pH
            buffer_name: Nama titik kalibrasi (misal: "6.86 (Titik Netral)")
            scaled_value: Nilai pH yang sudah diskalakan untuk ditulis
            use_command_register: Gunakan command register (True) atau hanya value register (False)
            
        Returns:
            bool: True jika berhasil, False jika gagal
        """
        try:
            logger.info(f"[CONFIG] Mulai kalibrasi pH: {buffer_name}")
            logger.info(f"   -> Slave ID: {unit_id}, Nilai: {scaled_value}")
            
            # 1. Tulis nilai pH target ke register
            if not self.modbus.write_register(unit_id, PH_CALIBRATION_REGISTER, scaled_value):
                logger.error(f"[ERROR] Gagal menulis nilai ke register {PH_CALIBRATION_REGISTER}")
                return False
            
            time.sleep(1)
            
            # 2. Tulis command SIMPAN jika diperlukan
            if use_command_register:
                if not self.modbus.write_register(unit_id, PH_COMMAND_REGISTER, PH_COMMAND_SAVE):
                    logger.error(f"❌ Gagal menulis command ke register {PH_COMMAND_REGISTER}")
                    return False
                
                # Beri waktu sensor untuk memproses
                logger.info(f"   ⏳ Menunggu sensor memproses (5 detik)...")
                time.sleep(5.0)
            
            logger.info(f"[OK] Kalibrasi {buffer_name} berhasil!")
            return True
            
        except Exception as e:
            logger.error(f"[ERROR] Error saat kalibrasi: {e}")
            return False
    
    def calibrate_multi_point(
        self,
        unit_id: int,
        buffer_sequence: list = None
    ) -> Dict[str, bool]:
        """
        Kalibrasi multi-titik secara berurutan
        
        Args:
            unit_id: Slave ID sensor pH
            buffer_sequence: List of buffer names dalam urutan kalibrasi
                            Jika None, gunakan default dari config
            
        Returns:
            Dict[str, bool]: Status kalibrasi untuk setiap buffer
        """
        if buffer_sequence is None:
            buffer_sequence = list(self.calibration_points.keys())
        
        logger.info(f"\n{'='*60}")
        logger.info(f"[CALIBRATE] KALIBRASI MULTI-TITIK - SLAVE ID {unit_id}")
        logger.info(f"{'='*60}")
        logger.info(f"Urutan kalibrasi: {', '.join(buffer_sequence)}")
        logger.info(f"Tekan ENTER untuk melanjutkan ke titik berikutnya...")
        logger.info(f"{'='*60}\n")
        
        results = {}
        
        for i, buffer_name in enumerate(buffer_sequence, 1):
            if buffer_name not in self.calibration_points:
                logger.warning(f"[WARN] Buffer '{buffer_name}' tidak ditemukan dalam config")
                results[buffer_name] = False
                continue
            
            scaled_value = self.calibration_points[buffer_name]
            
            logger.info(f"\n[{i}/{len(buffer_sequence)}] Siapkan buffer: {buffer_name}")
            input("Tekan ENTER untuk mulai kalibrasi...")
            
            success = self.calibrate_single_point(unit_id, buffer_name, scaled_value)
            results[buffer_name] = success
            
            if success:
                logger.info(f"[OK] {buffer_name} - OK")
            else:
                logger.error(f"[ERROR] {buffer_name} - GAGAL")
                logger.info("Lanjutkan ke buffer berikutnya? (y/n)")
                if input().lower() != 'y':
                    break
        
        # Summary
        logger.info(f"\n{'='*60}")
        logger.info("[INFO] RINGKASAN KALIBRASI:")
        successful = sum(1 for v in results.values() if v)
        logger.info(f"   Berhasil: {successful}/{len(results)}")
        for buffer_name, success in results.items():
            status = "[OK]" if success else "[ERROR]"
            logger.info(f"   {buffer_name}: {status}")
        logger.info(f"{'='*60}\n")
        
        return results
    
    def read_ph_value(self, unit_id: int, register_address: int = 0) -> Optional[float]:
        """
        Baca nilai pH dari sensor
        
        Args:
            unit_id: Slave ID sensor
            register_address: Alamat register untuk membaca nilai pH
            
        Returns:
            Optional[float]: Nilai pH atau None jika gagal
        """
        try:
            raw_values = self.modbus.read_registers(unit_id, register_address, 1)
            if raw_values:
                return raw_values[0] / 10.0
            return None
        except Exception as e:
            logger.error(f"Error membaca pH: {e}")
            return None


def main():
    """CLI untuk kalibrasi sensor pH"""
    calibrator = PHCalibrator()
    
    try:
        if not calibrator.connect():
            logger.error("Gagal terhubung ke Modbus")
            return
        
        logger.info("System monitoring tanah - Mode Kalibrasi pH")
        unit_id = int(input("Masukkan Slave ID: "))
        
        logger.info("\n1. Kalibrasi Single Point")
        logger.info("2. Kalibrasi Multi-Point")
        choice = input("Pilih mode (1/2): ")
        
        if choice == "1":
            buffer_name = input("Masukkan nama buffer (misal: 6.86 (Titik Netral)): ")
            scaled_value = int(input("Masukkan nilai pH yang sudah diskalakan: "))
            calibrator.calibrate_single_point(unit_id, buffer_name, scaled_value)
        elif choice == "2":
            calibrator.calibrate_multi_point(unit_id)
        else:
            logger.error("Pilihan tidak valid")
    
    except Exception as e:
        logger.error(f"Error: {e}")
    finally:
        calibrator.disconnect()


if __name__ == "__main__":
    main()
