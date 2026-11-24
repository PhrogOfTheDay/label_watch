from config.config import csv_path, data_dir, duckdb_path
import duckdb

db_path = duckdb_path.resolve()

con = duckdb.connect(str(db_path), read_only=True)

df = con.execute(f"""
SELECT * from options_drugs 
""").fetchdf()
print(df)
con.close()
