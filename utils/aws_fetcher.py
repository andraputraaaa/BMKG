import json
import os
import requests
import time
import threading
from utils.ibf_calculator import calculate_ibf_risk
from utils.raster_processor import process_landcover_tiles, get_dem_elevation

REGIONAL_FILE = os.path.join('data', 'indonesia_514_regencies.json')
BMKG_WEATHER_URL = 'https://api.bmkg.go.id/publik/prakiraan-cuaca'
BMKG_REQUEST_TIMEOUT = 10
BMKG_MIN_REQUEST_INTERVAL = 0.5
BMKG_MAX_RETRIES = 3
BMKG_CACHE_FILE = os.path.join('data', 'bmkg_weather_cache.json')
BMKG_STAGING_CACHE_FILE = os.path.join('data', 'bmkg_weather_cache.staging.json')
BMKG_CACHE_TTL = 600
BMKG_REQUEST_HEADERS = {
    'Accept': 'application/json, text/plain, */*',
    'Origin': 'https://www.bmkg.go.id',
    'Referer': 'https://www.bmkg.go.id/',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                  'AppleWebKit/537.36 (KHTML, like Gecko) '
                  'Chrome/131.0.0.0 Safari/537.36',
}
WEATHER_CACHE = {}
WEATHER_CACHE_TIMESTAMPS = {}
_LAST_BMKG_REQUEST_AT = 0.0
_WEATHER_DATA_READY = False
_WEATHER_REFRESH_LOCK = threading.Lock()

# Backup Stasiun Utama jika JSON belum di-extract dari SHP
DEFAULT_AWS_STATIONS = {
    "Jakarta Pusat": {"prov_code": "3100", "lat": -6.2088, "lon": 106.8456},
    "Banda Aceh": {"prov_code": "1100", "lat": 5.5483, "lon": 95.3238},
    "Medan": {"prov_code": "1200", "lat": 3.5952, "lon": 98.6722},
    "Surabaya": {"prov_code": "3500", "lat": -7.2575, "lon": 112.7521},
    "Makassar": {"prov_code": "7300", "lat": -5.1477, "lon": 119.4327},
    "Jayapura": {"prov_code": "9100", "lat": -2.5489, "lon": 140.7186}
}

def load_weather_cache():
    if not os.path.exists(BMKG_CACHE_FILE):
        return {}, {}
    try:
        with open(BMKG_CACHE_FILE, 'r', encoding='utf-8') as file:
            payload = json.load(file)
        weather_cache = {}
        cache_timestamps = {}
        for adm4, entry in payload.items():
            cached_at = float(entry['cached_at'])
            weather_cache[adm4] = entry['weather']
            cache_timestamps[adm4] = cached_at
        return weather_cache, cache_timestamps
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        print(f"[WARNING] Cache cuaca BMKG tidak dapat dibaca: {error}")
        return {}, {}

def save_weather_cache(cache=None, timestamps=None, cache_file=None):
    cache = WEATHER_CACHE if cache is None else cache
    timestamps = WEATHER_CACHE_TIMESTAMPS if timestamps is None else timestamps
    cache_file = BMKG_CACHE_FILE if cache_file is None else cache_file
    try:
        os.makedirs(os.path.dirname(cache_file), exist_ok=True)
        payload = {
            adm4: {
                'cached_at': timestamps[adm4],
                'weather': weather
            } for adm4, weather in cache.items()
        }
        with open(cache_file, 'w', encoding='utf-8') as file:
            json.dump(payload, file, ensure_ascii=False)
        return True
    except OSError as error:
        print(f"[WARNING] Cache cuaca BMKG tidak dapat disimpan: {error}")
        return False

WEATHER_CACHE, WEATHER_CACHE_TIMESTAMPS = load_weather_cache()
_WEATHER_DATA_READY = bool(WEATHER_CACHE)

def load_master_regions():
    """Membaca data wilayah dari file JSON hasil ekstraksi SHP."""
    if os.path.exists(REGIONAL_FILE):
        try:
            with open(REGIONAL_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error membaca {REGIONAL_FILE}: {e}")
    return []

def fetch_bmkg_weather(
    adm4,
    cache=None,
    timestamps=None,
    persist=True
):
    """Mengambil prakiraan cuaca BMKG untuk satu kode wilayah ADM4."""
    if not adm4:
        raise ValueError('Kode wilayah ADM4 tidak tersedia untuk wilayah BMKG')

    cache = WEATHER_CACHE if cache is None else cache
    timestamps = WEATHER_CACHE_TIMESTAMPS if timestamps is None else timestamps
    cached_at = timestamps.get(adm4)
    if (
        adm4 in cache
        and cached_at is not None
        and time.time() - cached_at < BMKG_CACHE_TTL
    ):
        return cache[adm4]
    global _LAST_BMKG_REQUEST_AT
    response = None
    for attempt in range(BMKG_MAX_RETRIES + 1):
        wait_time = BMKG_MIN_REQUEST_INTERVAL - (
            time.monotonic() - _LAST_BMKG_REQUEST_AT
        )
        if wait_time > 0:
            time.sleep(wait_time)

        response = requests.get(
            BMKG_WEATHER_URL,
            params={'adm4': adm4},
            headers=BMKG_REQUEST_HEADERS,
            timeout=BMKG_REQUEST_TIMEOUT
        )
        _LAST_BMKG_REQUEST_AT = time.monotonic()

        if response.status_code != 429 or attempt == BMKG_MAX_RETRIES:
            break

        retry_after = response.headers.get('Retry-After')
        try:
            retry_delay = float(retry_after)
        except (TypeError, ValueError):
            retry_delay = 2 ** attempt
        time.sleep(max(retry_delay, 1.0))

    response.raise_for_status()
    payload = response.json()

    try:
        forecast_groups = payload['data'][0]['cuaca']
        if not forecast_groups:
            raise ValueError(f'BMKG belum menyediakan prakiraan untuk {adm4}')
        forecast = next(
            forecast_item
            for forecast_group in forecast_groups
            if forecast_group
            for forecast_item in forecast_group
        )
    except (KeyError, IndexError, TypeError, StopIteration) as error:
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
    cache[adm4] = weather_data
    timestamps[adm4] = time.time()
    if persist:
        save_weather_cache(cache, timestamps)
    return weather_data


def refresh_weather_cache(regions):
    """Refresh weather data without blocking API responses."""
    global WEATHER_CACHE, WEATHER_CACHE_TIMESTAMPS
    staging_cache = dict(WEATHER_CACHE)
    staging_timestamps = dict(WEATHER_CACHE_TIMESTAMPS)

    for region in regions:
        adm4 = region.get('adm4')
        try:
            fetch_bmkg_weather(
                adm4,
                cache=staging_cache,
                timestamps=staging_timestamps,
                persist=False
            )
        except (requests.RequestException, ValueError) as error:
            print(
                f"[WARNING] Refresh cuaca gagal untuk "
                f"{region.get('region', 'Unknown')}: {error}"
            )

    if not save_weather_cache(
        staging_cache,
        staging_timestamps,
        BMKG_STAGING_CACHE_FILE
    ):
        return

    try:
        os.replace(BMKG_STAGING_CACHE_FILE, BMKG_CACHE_FILE)
    except OSError as error:
        print(f"[WARNING] Cache cuaca aktif tidak dapat ditukar: {error}")
        return
    WEATHER_CACHE = staging_cache
    WEATHER_CACHE_TIMESTAMPS = staging_timestamps


def start_background_weather_refresh(regions):
    if not _WEATHER_REFRESH_LOCK.acquire(blocking=False):
        return

    def run_refresh():
        try:
            refresh_weather_cache(regions)
        finally:
            _WEATHER_REFRESH_LOCK.release()

    thread = threading.Thread(target=run_refresh, daemon=True)
    thread.start()


def get_cached_weather(region, regions):
    """Return the latest cached weather, including stale data during refresh."""
    adm4 = region.get('adm4')
    if adm4 in WEATHER_CACHE:
        return WEATHER_CACHE[adm4]

    lat = float(region.get('lat', -2.5))
    lon = float(region.get('lon', 118.0))
    cached_candidates = [
        candidate for candidate in regions
        if candidate.get('adm4') in WEATHER_CACHE
        and candidate.get('code') != region.get('code')
    ]
    if not cached_candidates:
        return None

    candidate = min(
        cached_candidates,
        key=lambda item: (
            float(item.get('lat', -2.5)) - lat
        ) ** 2 + (
            float(item.get('lon', 118.0)) - lon
        ) ** 2
    )
    weather_data = dict(WEATHER_CACHE[candidate['adm4']])
    candidate_lat = float(candidate.get('lat', -2.5))
    candidate_lon = float(candidate.get('lon', 118.0))
    weather_data.update({
        'source': 'BMKG Public API (nearest ADM4 cache)',
        'source_adm4': candidate['adm4'],
        'source_region': candidate.get('region', 'Unknown'),
        'source_distance_degrees': round(
            ((candidate_lat - lat) ** 2 + (candidate_lon - lon) ** 2) ** 0.5,
            4
        )
    })
    return weather_data

def fetch_nearest_bmkg_weather(region, regions):
    """Menggunakan prakiraan BMKG dari ADM4 terdekat jika ADM4 utama gagal."""
    lat = float(region.get('lat', -2.5))
    lon = float(region.get('lon', 118.0))
    region_code = region.get('code')
    candidates = sorted(
        (
            candidate for candidate in regions
            if candidate.get('code') != region_code and candidate.get('adm4')
        ),
        key=lambda candidate: (
            float(candidate.get('lat', -2.5)) - lat
        ) ** 2 + (
            float(candidate.get('lon', 118.0)) - lon
        ) ** 2
    )

    cached_candidates = [
        candidate for candidate in candidates
        if candidate['adm4'] in WEATHER_CACHE
    ]
    if cached_candidates:
        candidate = cached_candidates[0]
        weather_data = dict(WEATHER_CACHE[candidate['adm4']])
        candidate_lat = float(candidate.get('lat', -2.5))
        candidate_lon = float(candidate.get('lon', 118.0))
        weather_data.update({
            'source': 'BMKG Public API (nearest ADM4 cache)',
            'source_adm4': candidate['adm4'],
            'source_region': candidate.get('region', 'Unknown'),
            'source_distance_degrees': round(
                ((candidate_lat - lat) ** 2 + (candidate_lon - lon) ** 2) ** 0.5,
                4
            )
        })
        return weather_data

    last_error = None
    for candidate in candidates:
        try:
            weather_data = dict(fetch_bmkg_weather(candidate['adm4']))
            candidate_lat = float(candidate.get('lat', -2.5))
            candidate_lon = float(candidate.get('lon', 118.0))
            weather_data.update({
                'source': 'BMKG Public API (nearest ADM4)',
                'source_adm4': candidate['adm4'],
                'source_region': candidate.get('region', 'Unknown'),
                'source_distance_degrees': round(
                    ((candidate_lat - lat) ** 2 + (candidate_lon - lon) ** 2) ** 0.5,
                    4
                )
            })
            return weather_data
        except (requests.RequestException, ValueError) as error:
            last_error = error

    raise ValueError(
        f'Tidak ada prakiraan BMKG terdekat yang tersedia untuk '
        f"{region.get('region', 'wilayah')}"
    ) from last_error

def get_aws_weather_data():
    """Mengembalikan data EWS terintegrasi untuk seluruh wilayah."""
    global _WEATHER_DATA_READY
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

    if _WEATHER_DATA_READY:
        start_background_weather_refresh(regions)

    for reg in regions:
        lat = float(reg.get('lat', -2.5))
        lon = float(reg.get('lon', 118.0))
        p_code = str(reg.get('province_code', '0000'))
        r_name = str(reg.get('region', 'Kota/Kabupaten'))

        # 1. Prakiraan cuaca BMKG untuk wilayah administratif tingkat IV.
        if _WEATHER_DATA_READY:
            weather_data = get_cached_weather(reg, regions)
            if weather_data is None:
                print(f"[WARNING] Cache cuaca belum tersedia untuk {r_name}")
                continue
        else:
            try:
                weather_data = fetch_bmkg_weather(reg.get('adm4'))
            except (requests.RequestException, ValueError) as error:
                try:
                    weather_data = fetch_nearest_bmkg_weather(reg, regions)
                    print(
                        f"[WARNING] Wilayah {r_name} menggunakan "
                        f"prakiraan ADM4 terdekat: {error}"
                    )
                except ValueError as fallback_error:
                    print(f"[WARNING] Wilayah {r_name} dilewati: {fallback_error}")
                    continue

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

    if not results:
        raise RuntimeError('Tidak ada wilayah yang berhasil mendapatkan data cuaca BMKG')

    _WEATHER_DATA_READY = True
    return results