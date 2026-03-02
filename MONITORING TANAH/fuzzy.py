import numpy as np
import skfuzzy as fuzz
from skfuzzy import control as ctrl


# ==============================
# 1. DEFINISI VARIABEL FUZZY
# ==============================

# Input
ph = ctrl.Antecedent(np.arange(4.0, 8.6, 0.1), 'ph')              # pH tanah
temp = ctrl.Antecedent(np.arange(10.0, 45.1, 0.5), 'temp')        # suhu (°C)
moist = ctrl.Antecedent(np.arange(0.0, 100.1, 1.0), 'moist')      # kelembapan (%)
N = ctrl.Antecedent(np.arange(0.0, 250.1, 5.0), 'N')              # N (mg/kg)
P = ctrl.Antecedent(np.arange(0.0, 80.1, 2.0), 'P')               # P (mg/kg)
K = ctrl.Antecedent(np.arange(0.0, 300.1, 5.0), 'K')              # K (mg/kg)
sal = ctrl.Antecedent(np.arange(0.0, 5.1, 0.1), 'sal')            # salinitas (mis. dS/m)

# Output
health = ctrl.Consequent(np.arange(0.0, 100.1, 1.0), 'health')    # indeks kesehatan tanah (0–100)


# ======================================
# 2. FUNGSI KEANGGOTAAN
# ======================================

# pH tanah
ph['asam']   = fuzz.trapmf(ph.universe, [4.0, 4.0, 5.0, 6.0])
ph['netral'] = fuzz.trimf(ph.universe, [5.5, 6.5, 7.5])
ph['basa']   = fuzz.trapmf(ph.universe, [7.0, 8.0, 8.5, 8.5])

# Suhu tanah (°C)
temp['rendah'] = fuzz.trapmf(temp.universe, [10.0, 10.0, 20.0, 22.0])
temp['sedang'] = fuzz.trimf(temp.universe, [20.0, 27.0, 32.0])
temp['tinggi'] = fuzz.trapmf(temp.universe, [30.0, 35.0, 45.0, 45.0])

# Kelembapan tanah (%)
moist['kering'] = fuzz.trapmf(moist.universe, [0.0, 0.0, 20.0, 30.0])
moist['normal'] = fuzz.trimf(moist.universe, [25.0, 40.0, 55.0])
moist['basah']  = fuzz.trapmf(moist.universe, [50.0, 65.0, 100.0, 100.0])

# Nitrogen (mg/kg)
N['rendah'] = fuzz.trapmf(N.universe, [0.0, 0.0, 40.0, 60.0])
N['sedang'] = fuzz.trimf(N.universe, [50.0, 90.0, 130.0])
N['tinggi'] = fuzz.trapmf(N.universe, [120.0, 160.0, 250.0, 250.0])

# Fosfor (mg/kg)
P['rendah'] = fuzz.trapmf(P.universe, [0.0, 0.0, 15.0, 20.0])
P['sedang'] = fuzz.trimf(P.universe, [15.0, 27.0, 40.0])
P['tinggi'] = fuzz.trapmf(P.universe, [35.0, 50.0, 80.0, 80.0])

# Kalium (mg/kg)
K['rendah'] = fuzz.trapmf(K.universe, [0.0, 0.0, 80.0, 120.0])
K['sedang'] = fuzz.trimf(K.universe, [100.0, 150.0, 200.0])
K['tinggi'] = fuzz.trapmf(K.universe, [180.0, 230.0, 300.0, 300.0])

# Salinitas (dS/m)
sal['rendah'] = fuzz.trapmf(sal.universe, [0.0, 0.0, 1.5, 2.0])
sal['sedang'] = fuzz.trimf(sal.universe, [1.5, 2.5, 3.5])
sal['tinggi'] = fuzz.trapmf(sal.universe, [3.0, 4.0, 5.0, 5.0])

# Output: kesehatan tanah
health['buruk']  = fuzz.trapmf(health.universe, [0.0, 0.0, 30.0, 45.0])
health['sedang'] = fuzz.trimf(health.universe, [35.0, 55.0, 75.0])
health['baik']   = fuzz.trapmf(health.universe, [65.0, 80.0, 100.0, 100.0])


# ==============================
# 3. BASIS ATURAN
# ==============================

rule_list = []

# Rule 1: Kondisi ideal
rule_list.append(
    ctrl.Rule(
        ph['netral'] &
        moist['normal'] &
        temp['sedang'] &
        N['sedang'] &
        P['sedang'] &
        K['sedang'] &
        sal['rendah'],
        health['baik']
    )
)

# Rule 2: pH netral, NPK tinggi, kelembapan normal → baik
rule_list.append(
    ctrl.Rule(
        ph['netral'] &
        moist['normal'] &
        (N['tinggi'] | P['tinggi'] | K['tinggi']) &
        sal['rendah'],
        health['baik']
    )
)

# Rule 3: pH asam + NPK rendah → buruk
rule_list.append(
    ctrl.Rule(
        ph['asam'] &
        (N['rendah'] | P['rendah'] | K['rendah']),
        health['buruk']
    )
)

# Rule 4: pH basa + salinitas tinggi → buruk
rule_list.append(
    ctrl.Rule(
        ph['basa'] & sal['tinggi'],
        health['buruk']
    )
)

# Rule 5: tanah terlalu kering atau terlalu basah → sedang
rule_list.append(
    ctrl.Rule(
        (moist['kering'] | moist['basah']) &
        (N['sedang'] | P['sedang'] | K['sedang']) &
        ph['netral'],
        health['sedang']
    )
)

# Rule 6: pH agak bermasalah tapi NPK sedang, sal rendah → sedang
rule_list.append(
    ctrl.Rule(
        ((ph['asam'] | ph['basa']) &
         N['sedang'] & P['sedang'] & K['sedang'] &
         sal['rendah']),
        health['sedang']
    )
)

# Rule 7: suhu tinggi + tanah kering → buruk
rule_list.append(
    ctrl.Rule(
        temp['tinggi'] & moist['kering'],
        health['buruk']
    )
)

# Rule 8: suhu tinggi tapi kelembapan normal + NPK sedang → sedang
rule_list.append(
    ctrl.Rule(
        temp['tinggi'] & moist['normal'] &
        N['sedang'] & P['sedang'] & K['sedang'],
        health['sedang']
    )
)

# Rule 9: semua nutrisi rendah → buruk
rule_list.append(
    ctrl.Rule(
        N['rendah'] & P['rendah'] & K['rendah'],
        health['buruk']
    )
)

# Rule 10: nutrisi tinggi tapi kelembapan basah atau salinitas sedang → sedang
rule_list.append(
    ctrl.Rule(
        (N['tinggi'] | P['tinggi'] | K['tinggi']) &
        (moist['basah'] | sal['sedang']),
        health['sedang']
    )
)

health_ctrl = ctrl.ControlSystem(rule_list)
health_sim = ctrl.ControlSystemSimulation(health_ctrl)


# ==============================
# 4. FUNGSI PENJELASAN
# ==============================

def jelaskan_kondisi(
    ph_val,
    temp_val,
    moist_val,
    N_val,
    P_val,
    K_val,
    sal_val,
    kategori
):
    faktor_baik = []
    faktor_bermasalah = []

    # pH
    if 6.0 <= ph_val <= 7.5:
        faktor_baik.append(f"pH mendekati netral ({ph_val:.2f})")
    elif ph_val < 5.5:
        faktor_bermasalah.append(f"pH terlalu asam ({ph_val:.2f})")
    elif ph_val > 7.5:
        faktor_bermasalah.append(f"pH terlalu basa ({ph_val:.2f})")
    else:
        faktor_bermasalah.append(f"pH agak menyimpang dari netral ({ph_val:.2f})")

    # Suhu
    if 22.0 <= temp_val <= 32.0:
        faktor_baik.append(f"suhu tanah berada pada rentang sesuai tanaman tropis ({temp_val:.2f} °C)")
    elif temp_val < 20.0:
        faktor_bermasalah.append(f"suhu tanah terlalu rendah ({temp_val:.2f} °C)")
    elif temp_val > 35.0:
        faktor_bermasalah.append(f"suhu tanah terlalu tinggi ({temp_val:.2f} °C)")
    else:
        faktor_bermasalah.append(f"suhu tanah kurang ideal ({temp_val:.2f} °C)")

    # Kelembapan
    if 25.0 <= moist_val <= 55.0:
        faktor_baik.append(f"kelembapan tanah berada pada kondisi normal ({moist_val:.2f}%)")
    elif moist_val < 20.0:
        faktor_bermasalah.append(f"tanah terlalu kering ({moist_val:.2f}%)")
    elif moist_val > 60.0:
        faktor_bermasalah.append(f"tanah terlalu basah/jenuh ({moist_val:.2f}%)")
    else:
        faktor_bermasalah.append(f"kelembapan tanah kurang stabil ({moist_val:.2f}%)")

    # Nitrogen
    if 50.0 <= N_val <= 130.0:
        faktor_baik.append(f"kandungan nitrogen berada pada kisaran cukup ({N_val:.2f} mg/kg)")
    elif N_val < 50.0:
        faktor_bermasalah.append(f"kandungan nitrogen rendah ({N_val:.2f} mg/kg)")
    else:
        faktor_bermasalah.append(f"kandungan nitrogen tinggi ({N_val:.2f} mg/kg)")

    # Fosfor
    if 15.0 <= P_val <= 40.0:
        faktor_baik.append(f"kandungan fosfor berada pada kisaran cukup ({P_val:.2f} mg/kg)")
    elif P_val < 15.0:
        faktor_bermasalah.append(f"kandungan fosfor rendah ({P_val:.2f} mg/kg)")
    else:
        faktor_bermasalah.append(f"kandungan fosfor tinggi ({P_val:.2f} mg/kg)")

    # Kalium
    if 100.0 <= K_val <= 200.0:
        faktor_baik.append(f"kandungan kalium berada pada kisaran cukup ({K_val:.2f} mg/kg)")
    elif K_val < 100.0:
        faktor_bermasalah.append(f"kandungan kalium rendah ({K_val:.2f} mg/kg)")
    else:
        faktor_bermasalah.append(f"kandungan kalium tinggi ({K_val:.2f} mg/kg)")

    # Salinitas
    if sal_val < 2.0:
        faktor_baik.append(f"salinitas tanah rendah ({sal_val:.2f} dS/m)")
    elif sal_val <= 4.0:
        faktor_bermasalah.append(f"salinitas tanah mulai mengganggu ({sal_val:.2f} dS/m)")
    else:
        faktor_bermasalah.append(f"salinitas tanah tinggi ({sal_val:.2f} dS/m)")

    penjelasan = []

    penjelasan.append(f"Tanah dikategorikan {kategori} karena kombinasi kondisi fisik dan kimia yang terukur.")

    if faktor_baik:
        penjelasan.append("Faktor yang mendukung kondisi tanah:")
        for fb in faktor_baik:
            penjelasan.append(f"  - {fb}")
    else:
        penjelasan.append("Tidak ada faktor yang jelas mendukung kondisi tanah.")

    if faktor_bermasalah:
        penjelasan.append("Faktor yang menurunkan kualitas tanah:")
        for fb in faktor_bermasalah:
            penjelasan.append(f"  - {fb}")
    else:
        penjelasan.append("Tidak ditemukan faktor utama yang menurunkan kualitas tanah.")

    return "\n".join(penjelasan)


# ==============================
# 5. FUNGSI EVALUASI
# ==============================

def evaluasi_kesehatan_tanah(
    ph_val,
    temp_val,
    moist_val,
    N_val,
    P_val,
    K_val,
    sal_val
):
    health_sim.input['ph'] = ph_val
    health_sim.input['temp'] = temp_val
    health_sim.input['moist'] = moist_val
    health_sim.input['N'] = N_val
    health_sim.input['P'] = P_val
    health_sim.input['K'] = K_val
    health_sim.input['sal'] = sal_val

    health_sim.compute()

    nilai = health_sim.output['health']

    if nilai < 40:
        label = "buruk"
    elif nilai < 70:
        label = "sedang"
    else:
        label = "baik"

    penjelasan = jelaskan_kondisi(
        ph_val, temp_val, moist_val,
        N_val, P_val, K_val, sal_val,
        label
    )

    return nilai, label, penjelasan


# ==============================
# 6. MAIN: INPUT MANUAL
# ==============================

if __name__ == "__main__":
    print("=== Evaluasi Kesehatan Tanah (Fuzzy Mamdani) ===")
    try:
        ph_val = float(input("Masukkan pH tanah               : "))
        temp_val = float(input("Masukkan suhu tanah (°C)        : "))
        moist_val = float(input("Masukkan kelembapan tanah (%)   : "))
        N_val = float(input("Masukkan kandungan Nitrogen (mg/kg): "))
        P_val = float(input("Masukkan kandungan Fosfor (mg/kg)  : "))
        K_val = float(input("Masukkan kandungan Kalium (mg/kg)  : "))
        sal_val = float(input("Masukkan salinitas (mis. dS/m)  : "))

        nilai, label, penjelasan = evaluasi_kesehatan_tanah(
            ph_val, temp_val, moist_val, N_val, P_val, K_val, sal_val
        )

        print("\nHasil evaluasi fuzzy:")
        print(f"Indeks kesehatan tanah : {nilai:.2f} (0–100)")
        print(f"Kategori               : {label}")
        print("\nPenjelasan:")
        print(penjelasan)

    except Exception as e:
        print("Terjadi kesalahan input atau perhitungan:", e)
