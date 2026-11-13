"""Refresh the local BMKG weather snapshot used by the application."""

from utils.aws_fetcher import get_aws_weather_data


if __name__ == "__main__":
    results = get_aws_weather_data()
    print(f"[SUCCESS] Snapshot BMKG diperbarui untuk {len(results)} wilayah.")
