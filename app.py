from flask import Flask, render_template, jsonify, request
from concurrent.futures import ThreadPoolExecutor

from utils.bps_api import fetch_population_data
from utils.aws_fetcher import get_aws_weather_data
from utils.raster_processor import process_landcover_tiles, get_dem_elevation, check_shp_boundary
from utils.osm_processor import get_building_density
from utils.historical_processor import get_historical_disaster_count
from utils.ibf_calculator import calculate_ibf_risk

app = Flask(__name__)

SPATIAL_CACHE = {}
_CACHE_READY = False

def preload_spatial_features(item):
    city_name = item.get("region", item.get("city", "Kota/Kabupaten"))
    prov_code = str(item.get("province_code", item.get("prov_code", "0000")))
    coords = item.get("coordinates", [-2.5, 118.0])
    lat, lon = coords[0], coords[1]

    region_code = item.get("code", item.get("region_code"))
    land_info = process_landcover_tiles(lat, lon, region_code)
    dem_elevation = get_dem_elevation(lat, lon, region_code)
    shp_info = check_shp_boundary(lat, lon, region_code)
    building_count = get_building_density(lat, lon, region_code)
    history_count = get_historical_disaster_count(city_name)

    return (city_name, {
        "city_name": city_name,
        "prov_code": prov_code,
        "lat": lat,
        "lon": lon,
        "land_info": land_info,
        "dem_elevation": dem_elevation,
        "shp_info": shp_info,
        "building_count": building_count,
        "history_count": history_count
    })

def initialize_app_cache():
    global SPATIAL_CACHE, _CACHE_READY
    if _CACHE_READY:
        return
    print("\n[STARTUP] Memulai Pre-loading Data Spasial Statis 507 Wilayah ke RAM...")
    raw_ews_data = get_aws_weather_data()
    
    items_to_process = []
    if isinstance(raw_ews_data, list):
        items_to_process = raw_ews_data
    elif isinstance(raw_ews_data, dict):
        for city_name, w_info in raw_ews_data.items():
            w_info['city'] = city_name
            items_to_process.append(w_info)

    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = [executor.submit(preload_spatial_features, item) for item in items_to_process]
        for future in futures:
            city_name, spatial_data = future.result()
            SPATIAL_CACHE[city_name] = spatial_data

    print(f"[SUCCESS] Pre-loading selesai! {len(SPATIAL_CACHE)} wilayah tersimpan di RAM Server.\n")
    _CACHE_READY = True

def process_all_ibf_data(province_code='ALL'):
    """Fungsi pembantu kalkulasi IBF untuk seluruh wilayah."""
    population_data = fetch_population_data()
    raw_ews_data = get_aws_weather_data()
    
    items_to_process = []
    if isinstance(raw_ews_data, list):
        items_to_process = raw_ews_data
    elif isinstance(raw_ews_data, dict):
        for city_name, w_info in raw_ews_data.items():
            w_info['city'] = city_name
            items_to_process.append(w_info)

    results = []
    for item in items_to_process:
        city_name = item.get("region", item.get("city", "Kota/Kabupaten"))
        prov_code = str(item.get("province_code", item.get("prov_code", "0000")))

        if province_code not in ['ALL', '0000', ''] and prov_code != str(province_code):
            continue

        spatial_info = SPATIAL_CACHE.get(city_name, {})
        if not spatial_info:
            continue

        w_info = item.get("weather", {})
        pop_info = population_data.get(prov_code, item.get("population", {"kepadatan": 1250, "nama": "Indonesia"}))

        ibf_result = calculate_ibf_risk(
            weather_info=w_info,
            pop_info=pop_info,
            land_info=spatial_info['land_info'],
            dem_elevation=spatial_info['dem_elevation'],
            building_count=spatial_info['building_count']
        )

        w_payload = dict(w_info)
        w_payload['wind_speed'] = w_info.get('wind_speed', w_info.get('wind', 15))
        w_payload['rainfall'] = w_info.get('rainfall', w_info.get('rain', 10))

        results.append({
            "region": city_name,
            "city": city_name,
            "coordinates": [spatial_info['lat'], spatial_info['lon']],
            "province_code": prov_code,
            "weather": w_payload,
            "population": pop_info,
            "land_cover": spatial_info['land_info'],
            "elevation": spatial_info['dem_elevation'],
            "shp_boundary": spatial_info['shp_info'],
            "building_count": spatial_info['building_count'],
            "disaster_history_count": spatial_info['history_count'],
            "ibf_status": ibf_result
        })

    return results

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/ibf-ews-data', methods=['GET'])
def get_ibf_ews_data():
    try:
        initialize_app_cache()
        province_code = request.args.get('province_code', 'ALL')
        results = process_all_ibf_data(province_code)

        return jsonify({
            "success": True,
            "status": "success",
            "mode": province_code,
            "total_regions": len(results),
            "data": results
        })

    except Exception as e:
        print(f"Error pada /api/ibf-ews-data: {e}")
        return jsonify({"success": False, "status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    initialize_app_cache()
    app.run(debug=True, port=5000)