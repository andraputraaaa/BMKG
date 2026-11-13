import functools
import json
import math
import os

DATA_DIR = 'data'
SPATIAL_DATA_FILE = os.path.join(DATA_DIR, 'spatial_data.json')
_SPATIAL_DATA = None

def _load_spatial_data():
    global _SPATIAL_DATA
    if _SPATIAL_DATA is None:
        try:
            with open(SPATIAL_DATA_FILE, 'r', encoding='utf-8') as file:
                _SPATIAL_DATA = json.load(file)
        except (FileNotFoundError, json.JSONDecodeError) as error:
            print(f"[ERROR] Gagal membaca {SPATIAL_DATA_FILE}: {error}")
            _SPATIAL_DATA = {}
    return _SPATIAL_DATA

def _get_spatial_record(lat, lon, region_code=None):
    data = _load_spatial_data()
    if region_code and str(region_code) in data:
        return data[str(region_code)]

    nearest = None
    nearest_distance = math.inf
    for record in data.values():
        try:
            distance = (float(record['lat']) - lat) ** 2 + (float(record['lon']) - lon) ** 2
        except (KeyError, TypeError, ValueError):
            continue
        if distance < nearest_distance:
            nearest = record
            nearest_distance = distance
    return nearest

@functools.lru_cache(maxsize=512)
def process_landcover_tiles(lat, lon, region_code=None):
    lat_r, lon_r = round(lat, 4), round(lon, 4)
    record = _get_spatial_record(lat_r, lon_r, region_code)
    if not record:
        return {"land_type": "Pemukiman / Built-up Area", "vulnerability_score": 3}
    return {
        "land_type": record.get("land_type", "Pemukiman / Built-up Area"),
        "vulnerability_score": int(record.get("vulnerability_score", 3))
    }

@functools.lru_cache(maxsize=512)
def get_dem_elevation(lat, lon, region_code=None):
    lat_r, lon_r = round(lat, 4), round(lon, 4)
    record = _get_spatial_record(lat_r, lon_r, region_code)
    if record and record.get("elevation") is not None:
        return float(record["elevation"])
    return float((abs(hash(f"{lat_r},{lon_r}")) % 35) + 5)


@functools.lru_cache(maxsize=512)
def check_shp_boundary(lat, lon, region_code=None):
    record = _get_spatial_record(round(lat, 4), round(lon, 4), region_code)
    if record:
        return {
            "provinsi": record.get("province", "Unknown"),
            "kabupaten": record.get("region", "Unknown"),
        }
    return {"provinsi": "Unknown", "kabupaten": "Unknown"}