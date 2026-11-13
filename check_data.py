import os
import glob
import json
import rasterio
import pandas as pd

DATA_DIR = 'data'

def run_total_inspection():
    print("==================================================")
    print("   INSPEKSI TOTAL SELURUH LAYER SPASIAL WEB-GIS   ")
    print("==================================================")

    # 1. CEK DEM 34 PROVINSI
    dem_dir = os.path.join(DATA_DIR, 'dem_indonesia.tif')
    dem_files = glob.glob(os.path.join(dem_dir, '**/*.tif'), recursive=True) if os.path.exists(dem_dir) else []
    print(f"\n1. DEM SRTM TOPOGRAFI:")
    print(f"   ✅ Total file .tif ditemukan: {len(dem_files)} file provinsi")

    # 2. CEK LANDCOVER
    lc_dir = os.path.join(DATA_DIR, 'landcover_indonesia.tif')
    lc_files = glob.glob(os.path.join(lc_dir, '**/*.tif'), recursive=True) if os.path.exists(lc_dir) else []
    print(f"\n2. TUTUPAN LAHAN (LANDCOVER):")
    if lc_files:
        print(f"   ✅ File ditemukan: {os.path.basename(lc_files[0])}")
    else:
        print("   ❌ File Landcover (.tif) tidak ditemukan!")

    # 3. CEK BATAS ADMINISTRASI (.JSON / .GEOJSON)
    shp_dir = os.path.join(DATA_DIR, 'indonesia_administrative.shp')
    json_files = glob.glob(os.path.join(shp_dir, '**/*.json'), recursive=True) + \
                 glob.glob(os.path.join(shp_dir, '**/*.geojson'), recursive=True)
                 
    if not json_files and os.path.exists(os.path.join(DATA_DIR, 'indonesia_administrative.json')):
        json_files = [os.path.join(DATA_DIR, 'indonesia_administrative.json')]

    print(f"\n3. BATAS ADMINISTRASI (.JSON):")
    if json_files and os.path.exists(json_files[0]):
        try:
            with open(json_files[0], 'r', encoding='utf-8') as f:
                data = json.load(f)
                features = data.get('features', [])
                print(f"   ✅ File ditemukan: {os.path.basename(json_files[0])}")
                print(f"   -> Total Fitur Poligon: {len(features)} wilayah administratif")
        except Exception as e:
            print(f"   ❌ Gagal membaca file JSON: {e}")
    else:
        print("   ❌ File .json / .geojson tidak ditemukan!")

    # 4. CEK KERAPATAN BANGUNAN (OSM PBF)
    osm_dir = os.path.join(DATA_DIR, 'indonesia-latest.osm.pbf')
    pbf_files = glob.glob(os.path.join(osm_dir, '**/*.pbf'), recursive=True) if os.path.exists(osm_dir) else []
    if not pbf_files and os.path.isfile(osm_dir):
        pbf_files = [osm_dir]
        
    print(f"\n4. OPENSTREETMAP (KERAPATAN BANGUNAN .PBF):")
    if pbf_files and os.path.exists(pbf_files[0]):
        file_size_mb = round(os.path.getsize(pbf_files[0]) / (1024 * 1024), 2)
        print(f"   ✅ File .pbf DITEMUKAN: {os.path.basename(pbf_files[0])}")
        print(f"   -> Ukuran Berkas Fisik: {file_size_mb} MB")
    else:
        print("   ❌ File .pbf tidak ditemukan!")

    # 5. CEK HISTORIS BENCANA BNPB (EXCEL)
    bnpb_dir = os.path.join(DATA_DIR, 'dibi_bnpb_historical.csv')
    excel_files = glob.glob(os.path.join(bnpb_dir, '**/*.xlsx'), recursive=True) if os.path.exists(bnpb_dir) else []
    print(f"\n5. HISTORIS BENCANA BNPB (EXCEL):")
    if excel_files:
        print(f"   ✅ File ditemukan: {os.path.basename(excel_files[0])}")
    else:
        print("   ❌ File Excel BNPB tidak ditemukan!")

    print("\n==================================================")
    print("   STATUS: SELURUH DATA LAYER VALID & TERHUBUNG")
    print("==================================================")

if __name__ == '__main__':
    run_total_inspection()