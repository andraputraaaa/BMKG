"""Convert the large local GIS sources into the JSON used by the web app.

Run this script on the machine that has the source TIFF and PBF files:
    python scripts/convert_spatial_data.py
"""

import json
import os
import argparse
from contextlib import ExitStack
from pathlib import Path

import rasterio
from rasterio.warp import transform
import osmium


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
REGIONS_FILE = DATA_DIR / "indonesia_514_regencies.json"
OUTPUT_FILE = DATA_DIR / "spatial_data.json"
LANDCOVER_DIR = DATA_DIR / "landcover_indonesia.tif"
DEM_DIR = DATA_DIR / "dem_indonesia.tif"
PBF_FILE = DATA_DIR / "indonesia-latest.osm.pbf"

LAND_TYPES = {
    1: "Pemukiman / Built-up Area",
    2: "Lahan Pertanian / Crops",
    3: "Semak Belukar / Shrub and Grassland",
    4: "Hutan / Trees",
    5: "Perairan / Water",
}

LANDCOVER_DEFAULT = 1

# Normalisasi kode kelas dari raster sumber menjadi lima kelas Indonesia.
LANDCOVER_CLASSES = {
    1: 4, 2: 4, 4: 4,
    5: 2,
    7: 1,
    10: 3,
    11: 5,
}


def raster_files(path):
    if path.is_file():
        return [path]
    return sorted(path.rglob("*.tif"))


def pbf_file(path):
    if path.is_file():
        return path
    files = sorted(path.rglob("*.pbf"))
    if files:
        return files[0]
    return None


class BuildingCounter(osmium.SimpleHandler):
    def __init__(self, regions):
        super().__init__()
        self.boxes = [
            (str(region["code"]), float(region["lon"]) - 0.02,
             float(region["lon"]) + 0.02, float(region["lat"]) - 0.02,
             float(region["lat"]) + 0.02)
            for region in regions
        ]
        self.counts = {code: 0 for code, *_ in self.boxes}

    def way(self, way):
        if "building" not in way.tags or not way.nodes:
            return
        try:
            lons = [node.lon for node in way.nodes]
            lats = [node.lat for node in way.nodes]
        except (RuntimeError, ValueError):
            return
        min_lon, max_lon = min(lons), max(lons)
        min_lat, max_lat = min(lats), max(lats)
        for code, west, east, south, north in self.boxes:
            if max_lon >= west and min_lon <= east and max_lat >= south and min_lat <= north:
                self.counts[code] += 1


def sample_raster(sources, lat, lon, default):
    for source in sources:
            x_value, y_value = lon, lat
            if source.crs and source.crs.to_string() != "EPSG:4326":
                xs, ys = transform("EPSG:4326", source.crs, [lon], [lat])
                x_value, y_value = xs[0], ys[0]
            if not (source.bounds.left <= x_value <= source.bounds.right and
                    source.bounds.bottom <= y_value <= source.bounds.top):
                continue
            row, col = source.index(x_value, y_value)
            if 0 <= row < source.height and 0 <= col < source.width:
                value = source.read(1, window=((row, row + 1), (col, col + 1)))[0, 0]
                if source.nodata is not None and value == source.nodata:
                    continue
                return float(value)
    return default


def landcover_info(value):
    raw_value = int(value)
    value = LANDCOVER_CLASSES.get(raw_value, LANDCOVER_DEFAULT)
    return {
        "land_value": value,
        "land_type": LAND_TYPES[value],
        "vulnerability_score": 3 if value == 1 else (2 if value in (2, 3) else 1),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--include-pbf",
        action="store_true",
        help="Also scan the large PBF to calculate building_count.",
    )
    args = parser.parse_args()

    with REGIONS_FILE.open("r", encoding="utf-8") as file:
        regions = json.load(file)

    dem_files = raster_files(DEM_DIR)
    landcover_files = raster_files(LANDCOVER_DIR)
    if not dem_files:
        raise FileNotFoundError(f"Tidak ada file DEM .tif di {DEM_DIR}")
    if not landcover_files:
        raise FileNotFoundError(f"Tidak ada file landcover .tif di {LANDCOVER_DIR}")
    result = {}
    building_counts = {}
    if args.include_pbf:
        source_pbf = pbf_file(PBF_FILE)
        if source_pbf is None:
            raise FileNotFoundError(f"File PBF tidak ditemukan: {PBF_FILE}")
        building_counter = BuildingCounter(regions)
        building_counter.apply_file(str(source_pbf), locations=True)
        building_counts = building_counter.counts
    elif OUTPUT_FILE.exists():
        with OUTPUT_FILE.open("r", encoding="utf-8") as file:
            previous_result = json.load(file)
        building_counts = {
            str(code): int(record["building_count"])
            for code, record in previous_result.items()
            if record.get("building_count") is not None
        }

    with ExitStack() as stack:
        dem_sources = [stack.enter_context(rasterio.open(filename)) for filename in dem_files]
        landcover_sources = [
            stack.enter_context(rasterio.open(filename)) for filename in landcover_files
        ]
        for index, region in enumerate(regions, start=1):
            lat = float(region["lat"])
            lon = float(region["lon"])
            elevation = sample_raster(dem_sources, lat, lon, 10.0)
            land_value = sample_raster(landcover_sources, lat, lon, LANDCOVER_DEFAULT)
            result[str(region["code"])] = {
                "region": region["region"],
                "province": region.get("province", "Unknown"),
                "lat": lat,
                "lon": lon,
                "elevation": max(1.0, round(elevation, 1)),
                **landcover_info(land_value),
                "building_count": building_counts.get(str(region["code"]), 120),
            }
            print(f"[{index}/{len(regions)}] {region['region']}")

    with OUTPUT_FILE.open("w", encoding="utf-8") as file:
        json.dump(result, file, ensure_ascii=False, separators=(",", ":"))
        file.write("\n")
    print(f"Selesai: {OUTPUT_FILE} ({len(result)} wilayah)")


if __name__ == "__main__":
    main()
