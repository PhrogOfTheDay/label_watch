import zipfile
from pathlib import Path
from urllib.parse import urlparse

import ijson
import pandas as pd
import requests
from rich.progress import track


cwd = Path(__file__).resolve().parent
ZIPPED_DATA_DIR = cwd / "json"
FINAL_CSV_PATH = cwd / "final" / "final_dataset.csv"
DOWNLOAD_URL = "https://api.fda.gov/download.json"
ENDPOINT = "label"  # Change to "event", "ndc", etc. if needed.
BATCH_SIZE = 500


def download_zip_files(endpoint: str, zipped_data_dir: Path) -> list[Path]:
    # Get the download links from the official openFDA manifest.
    response = requests.get(DOWNLOAD_URL, timeout=60)
    response.raise_for_status()
    dataset = response.json()["results"]["drug"][endpoint]
    zip_files = []

    for partition in track(dataset["partitions"], description="Downloading files"):
        url = partition["file"]
        # Keep the original folder structure: filenames may repeat across quarters.
        relative_path = urlparse(url).path.lstrip("/")
        zip_path = zipped_data_dir / dataset["export_date"] / relative_path
        zip_path.parent.mkdir(parents=True, exist_ok=True)

        # Reuse ZIP files already downloaded for this release.
        if not zipfile.is_zipfile(zip_path):
            temp_path = zip_path.with_suffix(".zip.part")
            try:
                with requests.get(url, stream=True, timeout=(15, 120)) as response:
                    response.raise_for_status()
                    with temp_path.open("wb") as file:
                        for chunk in response.iter_content(chunk_size=1024 * 1024):
                            file.write(chunk)

                if not zipfile.is_zipfile(temp_path):
                    raise ValueError(f"Invalid ZIP file: {url}")
                temp_path.replace(zip_path)
            finally:
                temp_path.unlink(missing_ok=True)

        zip_files.append(zip_path)

    return zip_files


def load_json_batches(zip_path: Path, batch_size: int = BATCH_SIZE):
    # Read JSON directly from the ZIP without extracting it to disk.
    if batch_size < 1:
        raise ValueError("Batch size must be positive")

    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        json_files = [name for name in zip_ref.namelist() if name.endswith(".json")]
        if not json_files:
            raise ValueError(f"No JSON files found in {zip_path}")

        for name in json_files:
            with zip_ref.open(name) as file:
                batch = []
                for record in ijson.items(file, "results.item", use_float=True):
                    if not isinstance(record, dict):
                        raise ValueError(f"Expected a JSON object in {zip_path}")
                    batch.append(record)

                    if len(batch) == batch_size:
                        df = pd.json_normalize(batch, sep=".")
                        batch = []
                        yield df

                # Process any records left over after the last full batch.
                if batch:
                    yield pd.json_normalize(batch, sep=".")


def create_csv_from_json(zip_files: list[Path], csv_path: Path = FINAL_CSV_PATH):
    if not zip_files:
        raise ValueError("No ZIP files found")

    # First pass: collect all unique columns, not all DataFrames.
    columns = set()
    total_rows = 0
    for zip_path in track(zip_files, description="Finding columns"):
        for df in load_json_batches(zip_path):
            columns.update(df.columns)
            total_rows += len(df)

    if not columns or not total_rows:
        raise ValueError("No records or columns found in the ZIP files")

    columns = sorted(columns)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = csv_path.with_suffix(".csv.part")

    # Second pass: align each batch to the same header and append to the CSV.
    # Write to a temporary file so an interrupted run cannot ruin an existing CSV.
    rows_written = 0
    try:
        with temp_path.open("w", encoding="utf-8", newline="") as file:
            for zip_path in track(zip_files, description="Writing CSV"):
                for df in load_json_batches(zip_path):
                    if set(df.columns) - set(columns):
                        raise ValueError(f"New columns found while writing {zip_path}")
                    df = df.reindex(columns=columns)
                    df.to_csv(file, index=False, header=(rows_written == 0))
                    rows_written += len(df)

        if rows_written != total_rows:
            raise ValueError("The number of records changed between passes")
        temp_path.replace(csv_path)
    finally:
        temp_path.unlink(missing_ok=True)

    print(f"Saved {rows_written:,} rows and {len(columns)} columns to {csv_path}")


def main():
    zip_files = download_zip_files(ENDPOINT, ZIPPED_DATA_DIR)

    # To use existing ZIPs instead, replace the line above with:
    # zip_files = sorted(ZIPPED_DATA_DIR.glob("*.zip"))
    # For a release in a subdirectory, select that specific release folder.

    create_csv_from_json(zip_files)


if __name__ == "__main__":
    main()
