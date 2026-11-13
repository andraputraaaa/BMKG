import os
import glob
import rasterio

# Path ke folder tempat 23 file .tif berada
LANDCOVER_DIR = os.path.join(os.path.dirname(__file__), "data", "landcover")
raster_files = glob.glob(os.path.join(LANDCOVER_DIR, "*.tif"))

if not raster_files:
    print("❌ File .tif tidak ditemukan di folder data/landcover!")
else:
    print(f"Total file .tif ditemukan: {len(raster_files)}\n" + "="*60)
    
    for i, filepath in enumerate(raster_files, 1):
        filename = os.path.basename(filepath)
        try:
            with rasterio.open(filepath) as src:
                print(f"[{i}] File: {filename}")
                print(f"    • System Koordinat (CRS): {src.crs}")
                print(f"    • Bounding Box (Bounds) : {src.bounds}")
                print(f"    • Ukuran (Px / Py)      : {src.width} x {src.height}")
                print(f"    • Nilai NoData          : {src.nodata}")
                print("-" * 60)
        except Exception as e:
            print(f"❌ Gagal membaca {filename}: {e}\n" + "-"*60)