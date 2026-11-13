import json
import os
import re

DATA_DIR = 'data'
JSON_FILE = os.path.join(DATA_DIR, 'indonesia_administrative.shp', 'indonesia_kota.json')
OUTPUT_JSON = os.path.join(DATA_DIR, 'indonesia_514_regencies.json')

# Master Kode Resmi Kemendagri / BPS 38 Provinsi
PROVINCE_NAME_TO_CODE = {
    "ACEH": "1100",
    "SUMATERA UTARA": "1200", "SUMUT": "1200",
    "SUMATERA BARAT": "1300", "SUMBAR": "1300",
    "RIAU": "1400",
    "JAMBI": "1500",
    "SUMATERA SELATAN": "1600", "SUMSEL": "1600",
    "BENGKULU": "1700",
    "LAMPUNG": "1800",
    "KEPULAUAN BANGKA BELITUNG": "1900", "BANGKA BELITUNG": "1900", "BABEL": "1900",
    "KEPULAUAN RIAU": "2100", "KEP. RIAU": "2100", "KEPRI": "2100",
    "DKI JAKARTA": "3100", "JAKARTA": "3100",
    "JAWA BARAT": "3200", "JABAR": "3200",
    "JAWA TENGAH": "3300", "JATENG": "3300",
    "DI YOGYAKARTA": "3400", "YOGYAKARTA": "3400", "DIY": "3400",
    "JAWA TIMUR": "3500", "JATIM": "3500",
    "BANTEN": "3600",
    "BALI": "5100",
    "NUSA TENGGARA BARAT": "5200", "NTB": "5200",
    "NUSA TENGGARA TIMUR": "5300", "NTT": "5300",
    "KALIMANTAN BARAT": "6100", "KALBAR": "6100",
    "KALIMANTAN TENGAH": "6200", "KALTENG": "6200",
    "KALIMANTAN SELATAN": "6300", "KALSEL": "6300",
    "KALIMANTAN TIMUR": "6400", "KALTIM": "6400",
    "KALIMANTAN UTARA": "6500", "KALTARA": "6500",
    "SULAWESI UTARA": "7100", "SULUT": "7100",
    "SULAWESI TENGAH": "7200", "SULTENG": "7200",
    "SULAWESI SELATAN": "7300", "SULSEL": "7300",
    "SULAWESI TENGGARA": "7400", "SULTRA": "7400",
    "GORONTALO": "7500",
    "SULAWESI BARAT": "7600", "SULBAR": "7600",
    "MALUKU UTARA": "8200", "MALUT": "8200",
    "MALUKU": "8100",
    "PAPUA BARAT DAYA": "9200",
    "PAPUA BARAT": "9100",
    "PAPUA SELATAN": "9300",
    "PAPUA TENGAH": "9500",
    "PAPUA PEGUNUNGAN": "9600",
    "PAPUA": "9400"
}

# Kamus Kabupaten/Kota Khusus untuk Kepri, Maluku Utara, dan Seluruh Wilayah Papua
CITY_RULES = [
    # KEPULAUAN RIAU (2100)
    ("2100", ["BATAM", "TANJUNG PINANG", "TANJUNGPINANG", "ANAMBAS", "KARIMUN", "LINGGA", "NATUNA", "KEPRI", "KEP. RIAU"]),
    
    # MALUKU UTARA (8200)
    ("8200", ["TERNATE", "TIDORE", "HALMAHERA", "SULA", "MOROTAI", "MALUKU UTARA", "MALUT"]),
    
    # MALUKU (8100)
    ("8100", ["AMBON", "TUAL", "ARU", "BURU", "MBD", "SBB", "SBT", "TANIMBAR", "MALUKU TENGGARA"]),
    
    # PAPUA BARAT (9100)
    ("9100", ["MANOKWARI", "FAKFAK", "FAK FAK", "KAIMANA", "TELUK BINTUNI", "TELUK WONDAMA", "PAPUA BARAT"]),
    
    # PAPUA BARAT DAYA (9200)
    ("9200", ["SORONG", "RAJA AMPAT", "TAMBRAUW", "MAYBRAT"]),
    
    # PAPUA SELATAN (9300)
    ("9300", ["MERAUKE", "BOVEN DIGOEL", "MAPPI", "ASMAT"]),
    
    # PAPUA TENGAH (9500)
    ("9500", ["NABIRE", "MIMIKA", "PANIAI", "DOGIYAI", "DEIYAI", "INTAN JAYA", "PUNCAK"]),
    
    # PAPUA PEGUNUNGAN (9600)
    ("9600", ["JAYAWIJAYA", "LANNY JAYA", "NDUGA", "YALIMO", "YAHUKIMO", "TOLIKARA", "PEGUNUNGAN BINTANG"]),
    
    # PAPUA INDUK (9400)
    ("9400", ["JAYAPURA", "BIAK", "KEEROM", "SARMI", "SUPIORI", "WAROPEN", "PAPUA"]),
    
    # JAWA BARAT, BANTEN, KALIMANTAN (Dipertahankan Presisi)
    ("3200", ["DEPOK", "BOGOR", "BEKASI", "BANDUNG", "CIMAHI", "TASIKMALAYA", "SUKABUMI", "CIREBON", "BANJAR", "KARAWANG", "PURWAKARTA", "SUBANG", "SUMEDANG", "GARUT", "CIANJUR", "MAJALENGKA", "KUNINGAN", "INDRAMAYU", "PANGANDARAN", "CIAMIS"]),
    ("3600", ["TANGERANG", "SERANG", "CILEGON", "PANDEGLANG", "LEBAK"]),
    ("3100", ["JAKARTA PUSAT", "JAKARTA UTARA", "JAKARTA BARAT", "JAKARTA SELATAN", "JAKARTA TIMUR", "KEPULAUAN SERIBU"]),
    ("6100", ["SINGKAWANG", "PONTIANAK", "SAMBAS", "BENGKAYANG", "KAPUAS HULU", "KAYONG", "KETAPANG", "KUBU RAYA", "LANDAK", "MELAWI", "MEMPAWAH", "SANGGAU", "SEKADAU", "SINTANG"]),
    ("1700", ["BENGKULU", "KAUR", "KEPAHIANG", "LEBONG", "MUKOMUKO", "REJANG LEBONG", "SELUMA"])
]

def resolve_province_code(props, kab_raw):
    # 1. Cek langsung dari atribut KDPROV
    kdprov = str(props.get('KDPROV', props.get('kdprov', props.get('province_code', '')))).strip()
    if kdprov and kdprov not in ['0', '0000', 'None', '']:
        return kdprov if len(kdprov) == 4 else kdprov.zfill(2) + "00"

    # 2. Cek gabungan seluruh teks atribut (PROVINSI / NAMOBJ / WADMPR / WADMKK)
    all_attr_text = " ".join([str(v) for v in props.values() if v is not None]).upper()
    kab_upper = str(kab_raw).upper().strip()

    # Cek kata kunci kabupaten/kota spesifik dulu
    for code, keywords in CITY_RULES:
        for kw in keywords:
            pattern = r'\b' + re.escape(kw) + r'\b'
            if re.search(pattern, kab_upper) or re.search(pattern, all_attr_text):
                return code

    # Cek atribut nama provinsi bawaan GeoJSON
    for prov_key, code in PROVINCE_NAME_TO_CODE.items():
        pattern = r'\b' + re.escape(prov_key) + r'\b'
        if re.search(pattern, all_attr_text):
            return code

    return "0000"

def extract_centroids_from_json():
    if not os.path.exists(JSON_FILE):
        print(f"[ERROR] File tidak ditemukan di path: {JSON_FILE}")
        return

    print(f"Membaca data geospasial dari: {JSON_FILE} ...")
    try:
        with open(JSON_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)

        features = data.get('features', []) if isinstance(data, dict) else data
        regions_list = []
        code_counts = {}

        for idx, feature in enumerate(features):
            props = feature.get('properties', {}) or {}
            geom = feature.get('geometry', {}) or {}

            prov_raw = str(props.get('PROVINSI', props.get('provinsi', props.get('WADMPR', props.get('NAMOBJ', 'Unknown')))))
            kab_raw = str(props.get('WADMKK', props.get('KABUPATEN', props.get('kabupaten', props.get('kota', props.get('region', 'Unknown'))))))

            lat, lon = None, None

            # Ekstrak Lat/Lon presisi dari geometry bawaan
            if 'lat' in props and 'lon' in props and props['lat'] is not None and props['lon'] is not None:
                lat, lon = float(props['lat']), float(props['lon'])
            elif geom and 'coordinates' in geom and geom['coordinates']:
                coords = geom['coordinates']
                if geom['type'] == 'Point':
                    lon, lat = coords[0], coords[1]
                else:
                    pts = coords[0] if geom['type'] == 'Polygon' else [pt for poly in coords for ring in poly for pt in ring]
                    if pts:
                        lons, lats = [p[0] for p in pts], [p[1] for p in pts]
                        lon = round((min(lons) + max(lons)) / 2.0, 4)
                        lat = round((min(lats) + max(lats)) / 2.0, 4)

            if lat is not None and lon is not None:
                p_code = resolve_province_code(props, kab_raw)
                code_counts[p_code] = code_counts.get(p_code, 0) + 1
                adm4 = str(props.get('KDEPUM', props.get('kdepum', ''))).strip()

                regions_list.append({
                    "code": str(idx + 1).zfill(4),
                    "adm4": adm4,
                    "province_code": p_code,
                    "province": prov_raw,
                    "region": kab_raw,
                    "lat": round(lat, 4),
                    "lon": round(lon, 4)
                })

        with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
            json.dump(regions_list, f, indent=2, ensure_ascii=False)

        print(f"\n[BERHASIL] Ekstraksi Selesai! Data tersimpan di {OUTPUT_JSON}")
        print("--- REKAPITULASI PEMETAAN WILAYAH ---")
        for code, count in sorted(code_counts.items()):
            print(f"Kode Provinsi {code}: {count} Wilayah")

    except Exception as e:
        print(f"[ERROR] Gagal membaca file JSON: {e}")

if __name__ == '__main__':
    extract_centroids_from_json()