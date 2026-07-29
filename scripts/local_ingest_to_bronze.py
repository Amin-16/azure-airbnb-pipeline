import os
import sys
import time
import random
import requests
from azure.storage.filedatalake import DataLakeServiceClient

# --- CONFIGURATION ---
CONNECTION_STRING = "KEY"
CONTAINER_NAME = "bronze"

if not CONNECTION_STRING:
    print("ERROR: Set the ADLS_CONN_STRING environment variable before running this script.")
    print('  PowerShell: $env:ADLS_CONN_STRING = "DefaultEndpointsProtocol=...;AccountKey=...;EndpointSuffix=core.windows.net"')
    sys.exit(1)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

MAX_RETRIES = 3
MIN_DELAY_SECONDS = 3
MAX_DELAY_SECONDS = 7

# --- THE 15 FILES ---
ingestion_map = [
    # Barcelona
    ("https://data.insideairbnb.com/spain/catalonia/barcelona/2025-09-14/data/listings.csv.gz", "airbnb/listings/city=barcelona/quarter=2025-Q3/listings.csv.gz"),
    ("https://data.insideairbnb.com/spain/catalonia/barcelona/2025-09-14/data/calendar.csv.gz", "airbnb/calendar/city=barcelona/quarter=2025-Q3/calendar.csv.gz"),
    ("https://data.insideairbnb.com/spain/catalonia/barcelona/2026-06-24/data/listings.csv.gz", "airbnb/listings/city=barcelona/quarter=2026-Q2/listings.csv.gz"),
    ("https://data.insideairbnb.com/spain/catalonia/barcelona/2026-06-24/data/calendar.csv.gz", "airbnb/calendar/city=barcelona/quarter=2026-Q2/calendar.csv.gz"),
    ("https://data.insideairbnb.com/spain/catalonia/barcelona/2026-06-24/visualisations/neighbourhoods.csv", "airbnb/neighbourhoods/city=barcelona/neighbourhoods.csv"),

    # New York City
    ("https://data.insideairbnb.com/united-states/ny/new-york-city/2025-12-11/data/listings.csv.gz", "airbnb/listings/city=new-york-city/quarter=2025-Q4/listings.csv.gz"),
    ("https://data.insideairbnb.com/united-states/ny/new-york-city/2025-12-11/data/calendar.csv.gz", "airbnb/calendar/city=new-york-city/quarter=2025-Q4/calendar.csv.gz"),
    ("https://data.insideairbnb.com/united-states/ny/new-york-city/2026-06-16/data/listings.csv.gz", "airbnb/listings/city=new-york-city/quarter=2026-Q2/listings.csv.gz"),
    ("https://data.insideairbnb.com/united-states/ny/new-york-city/2026-06-16/data/calendar.csv.gz", "airbnb/calendar/city=new-york-city/quarter=2026-Q2/calendar.csv.gz"),
    ("https://data.insideairbnb.com/united-states/ny/new-york-city/2026-06-16/visualisations/neighbourhoods.csv", "airbnb/neighbourhoods/city=new-york-city/neighbourhoods.csv"),

    # Lisbon
    ("https://data.insideairbnb.com/portugal/lisbon/lisbon/2025-09-21/data/listings.csv.gz", "airbnb/listings/city=lisbon/quarter=2025-Q3/listings.csv.gz"),
    ("https://data.insideairbnb.com/portugal/lisbon/lisbon/2025-09-21/data/calendar.csv.gz", "airbnb/calendar/city=lisbon/quarter=2025-Q3/calendar.csv.gz"),
    ("https://data.insideairbnb.com/portugal/lisbon/lisbon/2026-06-23/data/listings.csv.gz", "airbnb/listings/city=lisbon/quarter=2026-Q2/listings.csv.gz"),
    ("https://data.insideairbnb.com/portugal/lisbon/lisbon/2026-06-23/data/calendar.csv.gz", "airbnb/calendar/city=lisbon/quarter=2026-Q2/calendar.csv.gz"),
    ("https://data.insideairbnb.com/portugal/lisbon/lisbon/2026-06-23/visualisations/neighbourhoods.csv", "airbnb/neighbourhoods/city=lisbon/neighbourhoods.csv"),
]


def download_with_retry(url, max_retries=MAX_RETRIES):
    """Attempt to download a URL with retry + exponential backoff on failure."""
    for attempt in range(1, max_retries + 1):
        try:
            response = requests.get(url, headers=HEADERS, stream=True, timeout=60)
            if response.status_code == 200:
                return response
            else:
                print(f"   Attempt {attempt}/{max_retries} failed: HTTP {response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"   Attempt {attempt}/{max_retries} error: {e}")

        if attempt < max_retries:
            backoff = attempt * 5  # 5s, 10s, ... increasing backoff between retries
            print(f"   Retrying in {backoff}s...")
            time.sleep(backoff)

    return None


def main():
    print("Connecting to Azure Data Lake...")
    service_client = DataLakeServiceClient.from_connection_string(CONNECTION_STRING)
    file_system_client = service_client.get_file_system_client(file_system=CONTAINER_NAME)

    succeeded = []
    failed = []

    for i, (url, adls_path) in enumerate(ingestion_map, start=1):
        filename = url.split("/")[-1]
        city = adls_path.split("/")[2] if "/" in adls_path else "?"
        print(f"\n[{i}/{len(ingestion_map)}] Downloading {filename} for {city}...")

        response = download_with_retry(url)

        if response is not None:
            file_bytes = response.raw.read()
            size_mb = len(file_bytes) / (1024 * 1024)
            print(f"   Downloaded {size_mb:.1f} MB")
            upload_ok = False
            last_upload_error = None

            for upload_attempt in range(1, MAX_RETRIES + 1):
                try:
                    file_client = file_system_client.get_file_client(adls_path)
                    # Generous timeout: home upload speeds are often much
                    # slower than download speeds, and NYC's calendar file
                    # can be 200-300+ MB. 900s (15 min) gives headroom even
                    # on a slow upload connection (~0.3-0.5 MB/s worst case).
                    file_client.upload_data(
                        file_bytes,
                        overwrite=True,
                        connection_timeout=900,
                    )
                    print(f"   Uploaded to: {adls_path}")
                    succeeded.append(adls_path)
                    upload_ok = True
                    break
                except Exception as e:
                    last_upload_error = e
                    print(f"   Upload attempt {upload_attempt}/{MAX_RETRIES} failed: {e}")
                    if upload_attempt < MAX_RETRIES:
                        backoff = upload_attempt * 8
                        print(f"   Retrying upload in {backoff}s...")
                        time.sleep(backoff)

            if not upload_ok:
                failed.append((url, adls_path, f"upload error after retries: {last_upload_error}"))
        else:
            print(f"   Giving up on {filename} after {MAX_RETRIES} attempts.")
            failed.append((url, adls_path, "download failed after retries"))

        # Delay before the next request, even after success, to stay
        # under whatever rate limit tripped the earlier automated run.
        if i < len(ingestion_map):
            delay = random.uniform(MIN_DELAY_SECONDS, MAX_DELAY_SECONDS)
            print(f"   Waiting {delay:.1f}s before next request...")
            time.sleep(delay)

    print("\n" + "=" * 60)
    print(f"SUMMARY: {len(succeeded)} succeeded, {len(failed)} failed")
    print("=" * 60)

    if failed:
        print("\nFailed files (retry manually or re-run script for these):")
        for url, path, reason in failed:
            print(f"  - {url}")
            print(f"    -> target: {path}")
            print(f"    -> reason: {reason}")


if __name__ == "__main__":
    main()