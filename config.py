import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# BPS API Configuration
BPS_API_KEY = "1b7591ea4f62a838e000d1e8c0ec0be"

# Domain BPS untuk Agregat Nasional (Satu Indonesia)
BPS_DOMAIN_NATIONAL = "0000"

# Domain BPS untuk 38 Provinsi di Indonesia (Lengkap)
BPS_DOMAIN_ALL_PROVINCES = [
    # Sumatera
    "1100", "1200", "1300", "1400", "1500", "1600", "1700", "1800", "1900", "2100",
    # Jawa & Bali-Nusa Tenggara
    "3100", "3200", "3300", "3400", "3500", "3600", "5100", "5200", "5300",
    # Kalimantan
    "6100", "6200", "6300", "6400", "6500",
    # Sulawesi
    "7100", "7200", "7300", "7400", "7500", "7600",
    # Maluku & Papua
    "8100", "8200", "9100", "9200", "9400", "9500", "9600", "9700"
]

# AWS & Data Paths
LANDCOVER_DIR = os.path.join(BASE_DIR, "data", "landcover")
SHP_PATH = os.path.join(BASE_DIR, "data", "shp", "indonesia_kota.geojson")

# Threshold IBF
HAZARD_THRESHOLDS = {
    "wind_speed": {"low": 15, "medium": 25},  # knot
    "rainfall": {"low": 20, "medium": 50}     # mm/jam
}