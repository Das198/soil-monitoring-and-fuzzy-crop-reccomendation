"""
Fuzzy Logic - Sistem fuzzy untuk evaluasi kesehatan tanah
Merge dari fuzzy.py dan cbfuzzy.py
"""

import numpy as np
import skfuzzy as fuzz
from skfuzzy import control as ctrl
from typing import Dict, Tuple, Optional, List
from src.config import CROP_REQUIREMENTS
from src.utils.logger import get_logger

logger = get_logger(__name__)


class SoilFuzzyEvaluator:
    """Evaluator kesehatan tanah menggunakan Fuzzy Logic"""
    
    def __init__(self):
        """Inisialisasi fuzzy system untuk kesehatan tanah"""
        self._setup_fuzzy_system()
        self._setup_fuzzy_rules()
    
    def _setup_fuzzy_system(self) -> None:
        """Setup semesta pembicaraan dan fungsi keanggotaan"""
        
        # ===== INPUT UNIVERSES =====
        self.ph = ctrl.Antecedent(np.arange(4.0, 8.6, 0.1), 'ph')
        self.temp = ctrl.Antecedent(np.arange(10.0, 45.1, 0.5), 'temp')
        self.moist = ctrl.Antecedent(np.arange(0.0, 100.1, 1.0), 'moist')
        self.n = ctrl.Antecedent(np.arange(0.0, 250.1, 5.0), 'nitrogen')
        self.p = ctrl.Antecedent(np.arange(0.0, 80.1, 2.0), 'phosphor')
        self.k = ctrl.Antecedent(np.arange(0.0, 300.1, 5.0), 'potassium')
        self.sal = ctrl.Antecedent(np.arange(0.0, 5.1, 0.1), 'salinity')
        
        # ===== OUTPUT UNIVERSE =====
        self.health = ctrl.Consequent(np.arange(0.0, 100.1, 1.0), 'health')
        
        # ===== MEMBERSHIP FUNCTIONS - PH =====
        self.ph['asam'] = fuzz.trapmf(self.ph.universe, [4.0, 4.0, 5.0, 6.0])
        self.ph['netral'] = fuzz.trimf(self.ph.universe, [5.5, 6.5, 7.5])
        self.ph['basa'] = fuzz.trapmf(self.ph.universe, [7.0, 8.0, 8.5, 8.5])
        
        # ===== MEMBERSHIP FUNCTIONS - TEMPERATURE =====
        self.temp['rendah'] = fuzz.trapmf(self.temp.universe, [10.0, 10.0, 20.0, 22.0])
        self.temp['sedang'] = fuzz.trimf(self.temp.universe, [20.0, 27.0, 32.0])
        self.temp['tinggi'] = fuzz.trapmf(self.temp.universe, [30.0, 35.0, 45.0, 45.0])
        
        # ===== MEMBERSHIP FUNCTIONS - MOISTURE =====
        self.moist['kering'] = fuzz.trapmf(self.moist.universe, [0.0, 0.0, 20.0, 30.0])
        self.moist['normal'] = fuzz.trimf(self.moist.universe, [25.0, 40.0, 55.0])
        self.moist['basah'] = fuzz.trapmf(self.moist.universe, [50.0, 65.0, 100.0, 100.0])
        
        # ===== MEMBERSHIP FUNCTIONS - NITROGEN =====
        self.n['rendah'] = fuzz.trapmf(self.n.universe, [0.0, 0.0, 40.0, 60.0])
        self.n['sedang'] = fuzz.trimf(self.n.universe, [50.0, 90.0, 130.0])
        self.n['tinggi'] = fuzz.trapmf(self.n.universe, [120.0, 160.0, 250.0, 250.0])
        
        # ===== MEMBERSHIP FUNCTIONS - PHOSPHOR =====
        self.p['rendah'] = fuzz.trapmf(self.p.universe, [0.0, 0.0, 15.0, 20.0])
        self.p['sedang'] = fuzz.trimf(self.p.universe, [15.0, 27.0, 40.0])
        self.p['tinggi'] = fuzz.trapmf(self.p.universe, [35.0, 50.0, 80.0, 80.0])
        
        # ===== MEMBERSHIP FUNCTIONS - POTASSIUM =====
        self.k['rendah'] = fuzz.trapmf(self.k.universe, [0.0, 0.0, 50.0, 80.0])
        self.k['sedang'] = fuzz.trimf(self.k.universe, [70.0, 120.0, 170.0])
        self.k['tinggi'] = fuzz.trapmf(self.k.universe, [160.0, 200.0, 300.0, 300.0])
        
        # ===== MEMBERSHIP FUNCTIONS - SALINITY =====
        self.sal['rendah'] = fuzz.trapmf(self.sal.universe, [0.0, 0.0, 1.0, 1.5])
        self.sal['sedang'] = fuzz.trimf(self.sal.universe, [1.0, 2.0, 3.0])
        self.sal['tinggi'] = fuzz.trapmf(self.sal.universe, [2.5, 3.5, 5.0, 5.0])
        
        # ===== OUTPUT MEMBERSHIP FUNCTIONS - HEALTH =====
        self.health['buruk'] = fuzz.trapmf(self.health.universe, [0.0, 0.0, 20.0, 35.0])
        self.health['kurang'] = fuzz.trimf(self.health.universe, [25.0, 40.0, 55.0])
        self.health['baik'] = fuzz.trimf(self.health.universe, [50.0, 70.0, 85.0])
        self.health['sangat_baik'] = fuzz.trapmf(self.health.universe, [75.0, 85.0, 100.0, 100.0])
    
    def _setup_fuzzy_rules(self) -> None:
        """Setup fuzzy inference rules untuk evaluasi kesehatan tanah (30 rules)"""

        # ===== RULES DASAR (1-5) =====
        # Rule 1: pH netral, kelembapan normal, suhu sedang → Baik
        rule1 = ctrl.Rule(self.ph['netral'] & self.moist['normal'] & self.temp['sedang'], self.health['baik'])
        # Rule 2: pH asam & tanah kering → Kurang
        rule2 = ctrl.Rule(self.ph['asam'] & self.moist['kering'], self.health['kurang'])
        # Rule 3: NPK semua sedang → Baik
        rule3 = ctrl.Rule(self.n['sedang'] & self.p['sedang'] & self.k['sedang'], self.health['baik'])
        # Rule 4: Salah satu NPK rendah → Kurang
        rule4 = ctrl.Rule(self.n['rendah'] | self.p['rendah'] | self.k['rendah'], self.health['kurang'])
        # Rule 5: Salinitas tinggi → Buruk
        rule5 = ctrl.Rule(self.sal['tinggi'], self.health['buruk'])

        # ===== RULES KONDISI SANGAT BAIK (6-8) =====
        # Rule 6: pH netral, NPK tinggi → Sangat Baik
        rule6 = ctrl.Rule(self.ph['netral'] & self.n['tinggi'] & self.p['tinggi'] & self.k['tinggi'], self.health['sangat_baik'])
        # Rule 7: pH netral, NPK sedang, salinitas rendah → Sangat Baik
        rule7 = ctrl.Rule(self.ph['netral'] & self.n['sedang'] & self.p['sedang'] & self.k['sedang'] & self.sal['rendah'], self.health['sangat_baik'])
        # Rule 8: NPK tinggi, salinitas rendah → Sangat Baik
        rule8 = ctrl.Rule(self.n['tinggi'] & self.p['tinggi'] & self.k['tinggi'] & self.sal['rendah'], self.health['sangat_baik'])

        # ===== RULES KONDISI BURUK - pH BERMASALAH (9-12) =====
        # Rule 9: pH basa & salinitas tinggi → Buruk
        rule9 = ctrl.Rule(self.ph['basa'] & self.sal['tinggi'], self.health['buruk'])
        # Rule 10: pH asam, N rendah, P rendah → Buruk
        rule10 = ctrl.Rule(self.ph['asam'] & self.n['rendah'] & self.p['rendah'], self.health['buruk'])
        # Rule 11: pH basa & N rendah (pH tinggi menghambat fiksasi N) → Buruk
        rule11 = ctrl.Rule(self.ph['basa'] & self.n['rendah'], self.health['buruk'])
        # Rule 12: pH basa & P rendah (tanah alkalin mengikat P sehingga tidak tersedia) → Buruk
        rule12 = ctrl.Rule(self.ph['basa'] & self.p['rendah'], self.health['buruk'])

        # ===== RULES KONDISI BURUK - FISIK EKSTREM (13-15) =====
        # Rule 13: Suhu tinggi & kelembapan kering → Buruk
        rule13 = ctrl.Rule(self.temp['tinggi'] & self.moist['kering'], self.health['buruk'])
        # Rule 14: Semua NPK rendah → Buruk
        rule14 = ctrl.Rule(self.n['rendah'] & self.p['rendah'] & self.k['rendah'], self.health['buruk'])
        # Rule 15: pH asam + suhu tinggi + tanah kering (triple stress) → Buruk
        rule15 = ctrl.Rule(self.ph['asam'] & self.temp['tinggi'] & self.moist['kering'], self.health['buruk'])

        # ===== RULES KONDISI KURANG (16-22) =====
        # Rule 16: pH asam & salinitas sedang → Kurang
        rule16 = ctrl.Rule(self.ph['asam'] & self.sal['sedang'], self.health['kurang'])
        # Rule 17: Kelembapan basah & suhu tinggi (kondisi anaerobik) → Kurang
        rule17 = ctrl.Rule(self.moist['basah'] & self.temp['tinggi'], self.health['kurang'])
        # Rule 18: Suhu rendah & kelembapan kering → Kurang
        rule18 = ctrl.Rule(self.temp['rendah'] & self.moist['kering'], self.health['kurang'])
        # Rule 19: NPK tidak seimbang (N tinggi, P & K rendah) → Kurang
        rule19 = ctrl.Rule(self.n['tinggi'] & self.p['rendah'] & self.k['rendah'], self.health['kurang'])
        # Rule 20: Kelembapan basah & N rendah (leaching/pencucian N) → Kurang
        rule20 = ctrl.Rule(self.moist['basah'] & self.n['rendah'], self.health['kurang'])
        # Rule 21: Salinitas sedang & kelembapan kering (salinitas terkonsentrasi) → Kurang
        rule21 = ctrl.Rule(self.sal['sedang'] & self.moist['kering'], self.health['kurang'])
        # Rule 22: Suhu rendah & kelembapan basah (akar mudah busuk) → Kurang
        rule22 = ctrl.Rule(self.temp['rendah'] & self.moist['basah'], self.health['kurang'])

        # ===== RULES KONDISI BURUK - KOMBINASI SUHU & N (23) =====
        # Rule 23: Suhu rendah & N rendah (suhu dingin menghambat nitrifikasi) → Buruk
        rule23 = ctrl.Rule(self.temp['rendah'] & self.n['rendah'], self.health['buruk'])

        # ===== RULES KONDISI BAIK (24-27) =====
        # Rule 24: pH netral & N tinggi & kelembapan normal → Baik
        rule24 = ctrl.Rule(self.ph['netral'] & self.n['tinggi'] & self.moist['normal'], self.health['baik'])
        # Rule 25: NPK tinggi & salinitas sedang → Baik
        rule25 = ctrl.Rule(self.n['tinggi'] & self.p['tinggi'] & self.k['tinggi'] & self.sal['sedang'], self.health['baik'])
        # Rule 26: pH netral & salinitas rendah & N sedang → Baik
        rule26 = ctrl.Rule(self.ph['netral'] & self.sal['rendah'] & self.n['sedang'], self.health['baik'])
        # Rule 27: pH asam & kelembapan basah (asam + tergenang → anaerobik asam) → Kurang
        rule27 = ctrl.Rule(self.ph['asam'] & self.moist['basah'], self.health['kurang'])

        # ===== RULES KONDISI IDEAL SEMPURNA (28-30) =====
        # Rule 28: Semua faktor fisik ideal (pH netral, suhu sedang, moist normal, sal rendah) → Sangat Baik
        rule28 = ctrl.Rule(self.ph['netral'] & self.temp['sedang'] & self.moist['normal'] & self.sal['rendah'], self.health['sangat_baik'])
        # Rule 29: pH netral, NPK tinggi, salinitas rendah, kelembapan normal → Sangat Baik
        rule29 = ctrl.Rule(self.ph['netral'] & self.n['tinggi'] & self.p['tinggi'] & self.k['tinggi'] & self.sal['rendah'] & self.moist['normal'], self.health['sangat_baik'])
        # Rule 30: Kelembapan basah & suhu tinggi & salinitas tinggi (triple stress ekstrem) → Buruk
        rule30 = ctrl.Rule(self.moist['basah'] & self.temp['tinggi'] & self.sal['tinggi'], self.health['buruk'])

        self.system = ctrl.ControlSystem([
            rule1, rule2, rule3, rule4, rule5,
            rule6, rule7, rule8, rule9, rule10,
            rule11, rule12, rule13, rule14, rule15,
            rule16, rule17, rule18, rule19, rule20,
            rule21, rule22, rule23, rule24, rule25,
            rule26, rule27, rule28, rule29, rule30,
        ])
        self.simulator = ctrl.ControlSystemSimulation(self.system)
    
    def evaluate(self, sensor_data: Dict) -> Dict:
        """
        Evaluasi kesehatan tanah berdasarkan data sensor
        
        Args:
            sensor_data: Dictionary dengan keys: ph_tanah, suhu, kelembapan_tanah, 
                        nitrogen, fosfor, kalium, salinity
            
        Returns:
            Dict: Hasil evaluasi dengan health score dan rating
        """
        try:
            # Set input values
            self.simulator.input['ph'] = sensor_data.get('ph_tanah', 6.5)
            self.simulator.input['temp'] = sensor_data.get('suhu', 25)
            self.simulator.input['moist'] = sensor_data.get('kelembapan_tanah', 50)
            self.simulator.input['nitrogen'] = sensor_data.get('nitrogen', 100)
            self.simulator.input['phosphor'] = sensor_data.get('fosfor', 30)
            self.simulator.input['potassium'] = sensor_data.get('kalium', 100)
            self.simulator.input['salinity'] = sensor_data.get('salinity', 1.0)
            
            # Compute
            self.simulator.compute()
            
            health_score = self.simulator.output['health']
            rating = self._get_rating(health_score)
            
            return {
                'health_score': round(health_score, 2),
                'rating': rating,
                'details': {
                    'ph': sensor_data.get('ph_tanah'),
                    'temperature': sensor_data.get('suhu'),
                    'moisture': sensor_data.get('kelembapan_tanah'),
                    'nitrogen': sensor_data.get('nitrogen'),
                    'phosphor': sensor_data.get('fosfor'),
                    'potassium': sensor_data.get('kalium'),
                    'salinity': sensor_data.get('salinity')
                }
            }
            
        except Exception as e:
            logger.error(f"Error dalam evaluasi fuzzy: {e}")
            return {'health_score': None, 'rating': 'ERROR'}
    
    def _get_rating(self, health_score: float) -> str:
        """
        Konversi health score ke rating deskriptif
        
        Args:
            health_score: Score dari 0-100
            
        Returns:
            str: Rating deskriptif
        """
        if health_score >= 80:
            return "Sangat Baik"
        elif health_score >= 60:
            return "Baik"
        elif health_score >= 40:
            return "Kurang"
        else:
            return "Buruk"
    
    def check_crop_compatibility(
        self,
        sensor_data: Dict,
        crop_name: str
    ) -> Dict:
        """
        Cek kompatibilitas data sensor dengan kebutuhan tanaman tertentu
        
        Args:
            sensor_data: Dictionary data sensor
            crop_name: Nama tanaman (dari CROP_REQUIREMENTS)
            
        Returns:
            Dict: Hasil kompatibilitas untuk setiap parameter
        """
        if crop_name not in CROP_REQUIREMENTS:
            logger.warning(f"Tanaman '{crop_name}' tidak ditemukan")
            return {}
        
        requirements = CROP_REQUIREMENTS[crop_name]
        compatibility = {}
        
        # Mapping sensor ke requirements
        param_mapping = {
            'ph_tanah': 'ph',
            'suhu': 'temp',
            'kelembapan_tanah': 'moist',
            'nitrogen': 'n',
            'fosfor': 'p',
            'kalium': 'k',
            'salinity': 'sal'
        }
        
        for sensor_key, req_key in param_mapping.items():
            if sensor_key not in sensor_data or req_key not in requirements:
                continue
            
            sensor_val = sensor_data[sensor_key]
            min_val, max_val = requirements[req_key]
            
            if min_val <= sensor_val <= max_val:
                status = "OK"
                percentage = 100
            elif sensor_val < min_val:
                percentage = (sensor_val / min_val * 100) if min_val > 0 else 0
                status = "Terlalu Rendah"
            else:
                percentage = (max_val / sensor_val * 100)
                status = "Terlalu Tinggi"
            
            compatibility[sensor_key] = {
                'value': sensor_val,
                'range': [min_val, max_val],
                'status': status,
                'percentage': round(percentage, 1)
            }
        
        return compatibility

    def get_all_crop_recommendations(self, sensor_data: Dict) -> List[Dict]:
        """
        Mendapatkan skor kecocokan semua tanaman berdasarkan sensor data dan mengurutkannya.
        
        Args:
            sensor_data: Dictionary data sensor
            
        Returns:
            List of Dict yang berisi nama tanaman, skor rata-rata, status, dan rincian.
        """
        results = []
        for crop_name in CROP_REQUIREMENTS.keys():
            comp_data = self.check_crop_compatibility(sensor_data, crop_name)
            if not comp_data:
                continue
                
            percentages = [min(100.0, info['percentage']) for info in comp_data.values()]
            if not percentages:
                continue
            
            avg_score = sum(percentages) / len(percentages)
            avg_score = round(avg_score, 1)
            
            # Tentukan status global
            if avg_score >= 80:
                status = "Sangat Cocok"
            elif avg_score >= 60:
                status = "Cocok"
            elif avg_score >= 40:
                status = "Kurang Cocok"
            else:
                status = "Tidak Cocok"
                
            results.append({
                "nama": crop_name,
                "skor": avg_score,
                "status": status,
                "details": comp_data
            })
            
        # Urutkan berdasarkan skor terbesar ke terkecil
        results.sort(key=lambda x: x['skor'], reverse=True)
        return results

    def recommend_best_crops(self, sensor_data: Dict, top_n: int = 5) -> list:
        """
        Merekomendasikan tanaman terbaik berdasarkan data sensor saat ini.
        
        Args:
            sensor_data: Dictionary data sensor
            top_n: Jumlah rekomendasi teratas yang dikembalikan (default: 5)
            
        Returns:
            list: Daftar dictionary berisi tanaman dan skor rata-rata kecocokannya
        """
        recommendations = []
        
        for crop_name in CROP_REQUIREMENTS.keys():
            compat = self.check_crop_compatibility(sensor_data, crop_name)
            if not compat:
                continue
                
            # Hitung rata-rata persentase cocok
            total_percentage = 0
            param_count = len(compat)
            
            if param_count > 0:
                for param, data in compat.items():
                    # Batasi nilai persentase maksimum di 100% untuk dirata-rata
                    percentage = min(100.0, data['percentage'])
                    total_percentage += percentage
                    
                avg_score = total_percentage / param_count
                
                recommendations.append({
                    'crop': crop_name.capitalize(),
                    'score': round(avg_score, 1),
                    'details': compat
                })
            
        # Urutkan berdasarkan score tertinggi
        recommendations.sort(key=lambda x: x['score'], reverse=True)
        
        return recommendations[:top_n]


def main():
    """Test fuzzy evaluator"""
    evaluator = SoilFuzzyEvaluator()
    
    # Test data
    test_data = {
        'ph_tanah': 6.5,
        'suhu': 25,
        'kelembapan_tanah': 50,
        'nitrogen': 100,
        'fosfor': 30,
        'kalium': 100,
        'salinity': 1.0
    }
    
    result = evaluator.evaluate(test_data)
    logger.info(f"Hasil evaluasi: {result}")
    
    # Test crop compatibility (single)
    compat = evaluator.check_crop_compatibility(test_data, "maize") # Contoh diganti ke 'maize' sesuai format CSV
    logger.info(f"Kompatibilitas dengan maize (Jagung): {compat}")
    
    # Test top 5 recommendations
    top_crops = evaluator.recommend_best_crops(test_data, top_n=5)
    logger.info("\n--- Top 5 Rekomendasi Tanaman ---")
    for idx, crop in enumerate(top_crops, 1):
        logger.info(f"{idx}. {crop['crop']} (Skor Rata-rata: {crop['score']}%)")


if __name__ == "__main__":
    main()
