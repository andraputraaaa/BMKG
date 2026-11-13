import os
import json
import math

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

def _get_record(lat, lon, region_code=None):
    data = _load_spatial_data()
    if region_code and str(region_code) in data:
        return data[str(region_code)]
    return min(
        data.values(),
        key=lambda item: (float(item['lat']) - lat) ** 2 + (float(item['lon']) - lon) ** 2,
        default=None
    )

def get_building_density(lat, lon, region_code=None):
    record = _get_record(round(lat, 4), round(lon, 4), region_code)
    if record and record.get("building_count") is not None:
        return int(record["building_count"])
    return 120