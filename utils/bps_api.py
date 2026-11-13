import requests
from config import BPS_API_KEY, BPS_DOMAIN_ALL_PROVINCES

# Data Cadangan (Fallback) jika API BPS lambat / timeout / offline
DEFAULT_POPULATION_DATA = {
    "0000": {"nama": "Indonesia (Nasional)", "kepadatan": 143},
    "1100": {"nama": "Aceh", "kepadatan": 92},
    "1200": {"nama": "Sumatera Utara", "kepadatan": 205},
    "1300": {"nama": "Sumatera Barat", "kepadatan": 133},
    "1400": {"nama": "Riau", "kepadatan": 75},
    "1500": {"nama": "Jambi", "kepadatan": 73},
    "1600": {"nama": "Sumatera Selatan", "kepadatan": 98},
    "1700": {"nama": "Bengkulu", "kepadatan": 100},
    "1800": {"nama": "Lampung", "kepadatan": 260},
    "1900": {"nama": "Kep. Bangka Belitung", "kepadatan": 78},
    "2100": {"nama": "Kep. Riau", "kepadatan": 250},
    "3100": {"nama": "DKI Jakarta", "kepadatan": 15900},
    "3200": {"nama": "Jawa Barat", "kepadatan": 1360},
    "3300": {"nama": "Jawa Tengah", "kepadatan": 1113},
    "3400": {"nama": "DI Yogyakarta", "kepadatan": 1180},
    "3500": {"nama": "Jawa Timur", "kepadatan": 850},
    "3600": {"nama": "Banten", "kepadatan": 1230},
    "5100": {"nama": "Bali", "kepadatan": 750},
    "5200": {"nama": "Nusa Tenggara Barat", "kepadatan": 260},
    "5300": {"nama": "Nusa Tenggara Timur", "kepadatan": 110},
    "6100": {"nama": "Kalimantan Barat", "kepadatan": 37},
    "6200": {"nama": "Kalimantan Tengah", "kepadatan": 18},
    "6300": {"nama": "Kalimantan Selatan", "kepadatan": 105},
    "6400": {"nama": "Kalimantan Timur", "kepadatan": 29},
    "6500": {"nama": "Kalimantan Utara", "kepadatan": 10},
    "7100": {"nama": "Sulawesi Utara", "kepadatan": 180},
    "7200": {"nama": "Sulawesi Tengah", "kepadatan": 48},
    "7300": {"nama": "Sulawesi Selatan", "kepadatan": 197},
    "7400": {"nama": "Sulawesi Tenggara", "kepadatan": 71},
    "7500": {"nama": "Gorontalo", "kepadatan": 96},
    "7600": {"nama": "Sulawesi Barat", "kepadatan": 83},
    "8100": {"nama": "Maluku", "kepadatan": 39},
    "8200": {"nama": "Maluku Utara", "kepadatan": 40},
    "9100": {"nama": "Papua", "kepadatan": 12},
    "9200": {"nama": "Papua Barat", "kepadatan": 11},
    "9400": {"nama": "Papua Tengah", "kepadatan": 10},
    "9500": {"nama": "Papua Pegunungan", "kepadatan": 25},
    "9600": {"nama": "Papua Selatan", "kepadatan": 4},
    "9700": {"nama": "Papua Barat Daya", "kepadatan": 15}
}

def fetch_population_data(domain_code=None):
    """
    Mengambil data populasi dari BPS API dengan penanganan Timeout & Fallback.
    """
    population_data = {}
    var_id = "12"
    
    domains_to_fetch = [domain_code] if domain_code and domain_code not in ['ALL', '0000'] else BPS_DOMAIN_ALL_PROVINCES

    for domain in domains_to_fetch:
        url = f"https://webapi.bps.go.id/v1/api/list/model/data/lang/ind/domain/{domain}/var/{var_id}/key/{BPS_API_KEY}/"
        try:
            # Timeout dipersingkat ke 2 detik agar tidak menghambat Flask
            response = requests.get(url, timeout=2)
            if response.status_code == 200:
                data = response.json()
                if data.get("data-availability") == "available":
                    population_data[domain] = data.get("datacontent", {})
        except Exception:
            # Jika timeout / error, gunakan data fallback untuk domain tersebut
            population_data[domain] = DEFAULT_POPULATION_DATA.get(domain, {"kepadatan": 500, "nama": "Indonesia"})

    # Gabungkan dengan data default jika ada domain yang belum terisi
    for domain in BPS_DOMAIN_ALL_PROVINCES:
        if domain not in population_data:
            population_data[domain] = DEFAULT_POPULATION_DATA.get(domain, {"kepadatan": 500, "nama": "Indonesia"})

    return population_data