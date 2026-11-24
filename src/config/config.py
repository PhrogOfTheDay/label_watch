from pathlib import Path

top_level_dir = Path(__file__).resolve().parent.parent

data_dir = top_level_dir / "data"
duckdb_path = data_dir / "fda.duckdb"
csv_path = data_dir / "final" / "final_dataset.csv"
