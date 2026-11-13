import json
import os
import requests
from utils.ibf_calculator import calculate_ibf_risk
from utils.raster_processor import process_landcover_tiles, get_dem_elevation

REGIONAL_FILE = os.path.join('data', 'indonesia_514_regencies.json')
BMKG_WEATHER_URL = 'https://api.bmkg.go.id/publik/prakiraan-cuaca'
BMKG_REQUEST_TIMEOUT = 10
BMKG_REQUEST_HEADERS = {
    'Accept': 'application/json, text/plain, */*',
    'Origin': 'https://www.bmkg.go.id',
    'Referer': 'https://www.bmkg.go.id/',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                  'AppleWebKit/537.36 (KHTML, like Gecko) '
                  'Chrome/131.0.0.0 Safari/537.36',
}
WEATHER_CACHE = {}

# Backup Stasiun Utama jika JSON belum di-extract dari SHP
DEFAULT_AWS_STATIONS = {
    "Jakarta Pusat": {"prov_code": "3100", "lat": -6.2088, "lon": 106.8456},
    "Banda Aceh": {"prov_code": "1100", "lat": 5.5483, "lon": 95.3238},
    "Medan": {"prov_code": "1200", "lat": 3.5952, "lon": 98.6722},
    "Surabaya": {"prov_code": "3500", "lat": -7.2575, "lon": 112.7521},
    "Makassar": {"prov_code": "7300", "lat": -5.1477, "lon": 119.4327},
    "Jayapura": {"prov_code": "9100", "lat": -2.5489, "lon": 140.7186}
}

def load_master_regions():
    """Membaca data wilayah dari file JSON hasil ekstraksi SHP."""
    if os.path.exists(REGIONAL_FILE):
        try:
            with open(REGIONAL_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error membaca {REGIONAL_FILE}: {e}")
    return []

def fetch_bmkg_weather(adm4):
    """Mengambil prakiraan cuaca BMKG untuk satu kode wilayah ADM4."""
    if not adm4:
        raise ValueError('Kode wilayah ADM4 tidak tersedia untuk wilayah BMKG')

    if adm4 in WEATHER_CACHE:
        return WEATHER_CACHE[adm4]

    response = requests.get(
        BMKG_WEATHER_URL,
        params={'adm4': adm4},
        headers=BMKG_REQUEST_HEADERS,
        timeout=BMKG_REQUEST_TIMEOUT
    )
    response.raise_for_status()
    payload = response.json()

    try:
        forecast = payload['data'][0]['cuaca'][0][0]
    except (KeyError, IndexError, TypeError) as error:
        raise ValueError(f'Respons prakiraan BMKG tidak valid untuk {adm4}') from error

    wind_speed_ms = forecast.get('ws')
    rainfall = forecast.get('tp')
    if wind_speed_ms is None or rainfall is None:
        raise ValueError(f'Respons prakiraan BMKG tidak memiliki data cuaca untuk {adm4}')

    weather_data = {
        'wind_speed': round(float(wind_speed_ms) * 1.94384, 1),
        'rainfall': round(float(rainfall), 1),
        'pressure': 1012.0,
        'pressure_drop_3h': 0.0,
        'temperature': forecast.get('t'),
        'humidity': forecast.get('hu'),
        'weather': forecast.get('weather_desc'),
        'forecast_datetime': forecast.get('local_datetime'),
        'source': 'BMKG Public API'
    }
    WEATHER_CACHE[adm4] = weather_data
    return weather_data

def get_aws_weather_data():
    """Mengembalikan data EWS terintegrasi untuk seluruh wilayah."""
    regions = load_master_regions()
    results = []

    # FALLBACK: Jika file JSON belum ada, gunakan dictionary default
    if not regions:
        for city, info in DEFAULT_AWS_STATIONS.items():
            regions.append({
                "code": "0000",
                "province_code": info["prov_code"],
                "region": city,
                "lat": info["lat"],
                "lon": info["lon"]
            })

    for reg in regions:
        lat = float(reg.get('lat', -2.5))
        lon = float(reg.get('lon', 118.0))
        p_code = str(reg.get('province_code', '0000'))
        r_name = str(reg.get('region', 'Kota/Kabupaten'))

        # 1. Prakiraan cuaca BMKG untuk wilayah administratif tingkat IV.
        weather_data = fetch_bmkg_weather(reg.get('adm4'))

        # 2. Ekstraksi Data Spasial dari GeoTIFF Landcover & DEM SRTM
        region_code = reg.get('code')
        land_info = process_landcover_tiles(lat, lon, region_code)
        dem_elev = get_dem_elevation(lat, lon, region_code)

        # 3. Data Exposure Kepadatan Penduduk BPS
        pop_info = {"kepadatan": 3500 if "Kota" in r_name else 800}

        # 4. Kalkulasi Matriks Risiko IBF WMO-No. 1150
        ibf_res = calculate_ibf_risk(
            weather_info=weather_data,
            pop_info=pop_info,
            land_info=land_info,
            dem_elevation=dem_elev
        )

        results.append({
            "code": reg.get('code', '0000'),
            "province_code": p_code,
            "region": r_name,
            "coordinates": [lat, lon],
            "weather": weather_data,
            "land_cover": land_info,
            "dem_elevation": dem_elev,
            "population": pop_info,
            "ibf_status": ibf_res
        })

    return results