"""
Sensor Data Processor - Mapping dan scaling data dari register
"""

from typing import Dict, List, Optional
from src.config import REGISTER_MAP, SCALED_PARAMETERS
from src.utils.logger import get_logger

logger = get_logger(__name__)


class SensorData:
    """Processor untuk mengubah raw register menjadi sensor data yang meaningful"""
    
    def __init__(self, register_map: Dict[str, int] = None, scaled_params: List[str] = None):
        """
        Inisialisasi SensorData Processor
        
        Args:
            register_map: Mapping nama sensor ke index register
            scaled_params: List parameter yang perlu scaling 0.1
        """
        self.register_map = register_map or REGISTER_MAP
        self.scaled_parameters = scaled_params or SCALED_PARAMETERS
    
    def process_registers(self, raw_registers: List[int]) -> Optional[Dict[str, float]]:
        """
        Konversi raw register menjadi data sensor dengan mapping dan scaling
        
        Args:
            raw_registers: List nilai raw dari Modbus
            
        Returns:
            Dict[str, float]: Mapped dan scaled sensor data atau None jika error
        """
        try:
            if not raw_registers or len(raw_registers) < 8:
                logger.warning(f"Data register tidak lengkap: {len(raw_registers) if raw_registers else 0} values")
                return None
            
            mapped_data = {}
            
            for param_name, register_index in self.register_map.items():
                if register_index >= len(raw_registers):
                    logger.warning(f"Index register {register_index} melampaui panjang data")
                    continue
                
                raw_value = raw_registers[register_index]
                scaled_value = self._scale_parameter(param_name, raw_value)
                mapped_data[param_name] = scaled_value
            
            logger.debug(f"[OK] Data sensor diproses: {mapped_data}")
            return mapped_data
            
        except Exception as e:
            logger.error(f"Error saat memproses register: {e}")
            return None
    
    def _scale_parameter(self, param_name: str, raw_value: int) -> float:
        """
        Terapkan scaling pada parameter tertentu
        
        Args:
            param_name: Nama parameter sensor
            raw_value: Nilai raw dari register
            
        Returns:
            float: Nilai yang sudah diskalakan
        """
        if param_name in self.scaled_parameters:
            return raw_value / 10.0
        return float(raw_value)
    
    def format_output(self, sensor_data: Dict[str, float], unit_id: int = None, timestamp: str = None) -> Dict:
        """
        Format sensor data untuk output/pengiriman
        
        Args:
            sensor_data: Dictionary sensor data
            unit_id: ID slave Modbus (optional)
            timestamp: Timestamp pembacaan (optional)
            
        Returns:
            Dict: Formatted output dengan metadata
        """
        if not sensor_data:
            return {}
        
        output = {
            "data": sensor_data,
            "timestamp": timestamp,
            "slave_id": unit_id
        }
        
        # Hapus None values
        return {k: v for k, v in output.items() if v is not None}
    
    def get_readable_output(self, sensor_data: Dict[str, float]) -> str:
        """
        Generate readable text output dari sensor data
        
        Args:
            sensor_data: Dictionary sensor data
            
        Returns:
            str: Formatted readable output
        """
        if not sensor_data:
            return "Data sensor kosong"
        
        output_lines = []
        for name, value in sensor_data.items():
            # Format nama: kelembapan_tanah -> Kelembapan Tanah
            display_name = name.replace('_', ' ').title()
            output_lines.append(f"  > {display_name}: {value}")
        
        return "\n".join(output_lines)
