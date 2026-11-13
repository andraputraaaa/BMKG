import functools

def get_wind_label(wind_kts):
    if wind_kts >= 28:
        return "Sangat Kencang / Ekstrem"
    elif wind_kts >= 17:
        return "Angin Kencang"
    else:
        return "Lemah / Normal"

def get_rain_label(rain_rate):
    if rain_rate >= 20:
        return "Sangat Lebat / Ekstrem"
    elif rain_rate >= 10:
        return "Hujan Lebat"
    elif rain_rate >= 5:
        return "Hujan Sedang"
    else:
        return "Ringan / Cerah"

@functools.lru_cache(maxsize=256)
def calculate_hazard_score(wind_speed_kts, rain_rate_mm, pressure_hpa, dem_elevation=10.0, pressure_drop_3h=0.0):
    # 1. Evaluasi Angin (Skala BMKG & Beaufort)
    if wind_speed_kts >= 28:
        h_wind = 3
    elif wind_speed_kts >= 17:
        h_wind = 2
    else:
        h_wind = 1

    # 2. Evaluasi Hujan per Jam (Standar Intensitas BMKG)
    if rain_rate_mm >= 20.0:
        h_rain = 3
    elif rain_rate_mm >= 10.0:
        h_rain = 2
    else:
        h_rain = 1

    # 3. Evaluasi Tekanan Udara & Instabilitas Konvektif
    if pressure_hpa < 1000 or pressure_drop_3h >= 4.0:
        h_press = 3
    elif pressure_hpa <= 1007 or pressure_drop_3h >= 2.0:
        h_press = 2
    else:
        h_press = 1

    return max(h_wind, h_rain, h_press)

def calculate_ibf_risk(
    weather_info=None,
    pop_info=None,
    land_info=None,
    dem_elevation=10.0,
    building_count=120,
    **kwargs
):
    """Calculate predictive IBF risk using R = H x E x V.

    Historical disaster records are kept for validation and comparison in the
    API response; they are intentionally not part of the core risk index.
    """
    if weather_info is None: weather_info = {}
    if pop_info is None: pop_info = {}
    if land_info is None: land_info = {}

    wind = float(weather_info.get('wind_speed', weather_info.get('wind_kts', weather_info.get('wind', 0))) or 0)
    rain = float(weather_info.get('rainfall', weather_info.get('rain_rate', weather_info.get('rain', 0))) or 0)
    press = float(weather_info.get('pressure', weather_info.get('press', 1012)) or 1012)
    press_drop = float(weather_info.get('pressure_drop_3h', 0.0) or 0.0)

    wind_status = get_wind_label(wind)
    rain_status = get_rain_label(rain)

    # 1. Skor Hazard (H)
    h_score = calculate_hazard_score(wind, rain, press, dem_elevation, press_drop)

    # 2. Skor Exposure (E) - Standar BPS
    kepadatan = float(pop_info.get('kepadatan', 1000) or 1000)
    if kepadatan >= 7500 or building_count > 200:
        e_score = 3
    elif kepadatan >= 2000 or building_count > 80:
        e_score = 2
    else:
        e_score = 1

    # 3. Skor Vulnerability (V) - Raster Landcover & DEM
    v_base = int(land_info.get('vulnerability_score', 2) or 2)
    if dem_elevation < 10.0 and v_base < 3:
        v_score = v_base + 1
    else:
        v_score = v_base

    raw_ri = h_score * e_score * v_score

    # GATEKEEPER HAZARD KETAT & REKOMENDASI TEKNIS WMO-No. 1150
    if h_score == 1:
        if raw_ri >= 6:
            status = "WASPADA"
            color = "#FFFF00"
            action = "Waspadai potensi perubahan cuaca lokal secara mendadak serta perhatikan kondisi bangunan rentan."
        else:
            status = "AMAN"
            color = "#00FF00"
            action = "Kondisi dinamika atmosfer aman dan terkendali. Operasional masyarakat dapat berjalan normal."
    else:
        if raw_ri >= 18:
            status = "AWAS"
            color = "#FF0000"
            action = "Potensi angin kencang ekstrem / puting beliung. Waspadai struktur atap rapuh, baliho roboh, dan pohon tumbang."
        elif raw_ri >= 12:
            status = "SIAGA"
            color = "#FFA500"
            action = "Potensi hembusan angin kencang lokal. Waspadai dahan pohon patah dan penurunan jarak pandang saat berkendara."
        elif raw_ri >= 6:
            status = "WASPADA"
            color = "#FFFF00"
            action = "Waspadai pergerakan angin sedang hingga kencang di area terbuka serta tingkatkan kewaspadaan berkendara."
        else:
            status = "AMAN"
            color = "#00FF00"
            action = "Kondisi atmosfer secara umum kondusif. Tetap memantau pembaruan informasi cuaca harian BMKG."

    return {
        "status": status,
        "color": color,
        "color_code": color,
        "risk_level": status,
        "action": action,
        "rekomendasi": action,
        "wind_status": wind_status,
        "rain_status": rain_status,
        "scores": {
            "hazard": h_score,
            "exposure": e_score,
            "vulnerability": v_score,
            "risk_index": raw_ri
        }
    }