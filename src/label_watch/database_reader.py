import json
from pathlib import Path

from config.config import data_dir, duckdb_path, csv_path
import duckdb
import typer


if not duckdb_path.exists() and Path("fda.duckdb").resolve().exists():
    duckdb_path = Path("fda.duckdb").resolve()
con = duckdb.connect(duckdb_path.as_posix())


def build_dataset_cache() -> None:
    if not csv_path.is_file():
        raise FileNotFoundError(f"FDA dataset not found: {csv_path}")

    existing = con.execute("""
        SELECT 1
        FROM information_schema.tables
        WHERE table_name = 'final_dataset_cache'
        LIMIT 1
    """).fetchone()

    if existing:
        print(
            "final_dataset_cache already exists. Skipping import.",
            flush=True,
        )
        return

    csv_sql = csv_path.as_posix().replace("'", "''")

    con.execute(f"""
        CREATE TABLE final_dataset_cache AS
        SELECT
            set_id,
            id,
            version,
            effective_time,
            "openfda.brand_name",
            "openfda.generic_name",
            "openfda.manufacturer_name",
            "openfda.product_ndc",
            "openfda.package_ndc",
            "openfda.route",
            "openfda.product_type",
            dosage_forms_and_strengths
        FROM read_csv_auto(
            '{csv_sql}',
            all_varchar=true
        )
    """)


def initialize_db() -> None:
    con.execute(
        """
        CREATE SEQUENCE IF NOT EXISTS option_id_seq START 1;
        CREATE TABLE IF NOT EXISTS options (
            id INTEGER PRIMARY KEY DEFAULT nextval('option_id_seq'), 
            name VARCHAR NOT NULL,
            list_of_options VARCHAR[] NOT NULL
        );
        """
    )
    con.execute("DELETE FROM options WHERE id NOT IN (SELECT MIN(id) FROM options GROUP BY name);")
    con.execute(
        """
        INSERT INTO options (name, list_of_options)
        SELECT 
            'default_drug_info', 
            ARRAY[
                'boxed_warning', 'contraindications', 'warnings_and_precautions',
                'warnings', 'adverse_reactions', 'drug_interactions',
                'recent_major_changes', 'indications_and_usage',
                'dosage_and_administration', 'dosage_forms_and_strengths',
                'use_in_specific_populations', 'pregnancy',
                'pregnancy_or_breast_feeding', 'pediatric_use', 'geriatric_use'
            ]
        WHERE NOT EXISTS (SELECT 1 FROM options WHERE name = 'default_drug_info');
        """
    )
    con.execute(
        """
        CREATE SEQUENCE IF NOT EXISTS drug_id_seq START 1;
        CREATE TABLE IF NOT EXISTS tracked_drugs (
            product_id INTEGER PRIMARY KEY DEFAULT nextval('drug_id_seq'),
            set_id VARCHAR UNIQUE,
            brand_name VARCHAR,
            generic_name VARCHAR,
            manufacturer_name VARCHAR,
            dosage_form VARCHAR,
            route VARCHAR,
            product_type VARCHAR,
            product_ndc VARCHAR,
            package_ndc VARCHAR,
            effective_time VARCHAR
        );
        """
    )
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS options_drugs (
            option_id INTEGER REFERENCES options(id),
            product_id INTEGER REFERENCES tracked_drugs(product_id),
            PRIMARY KEY (option_id, product_id)
        );
        """
    )
    build_dataset_cache()
    typer.echo("Database initialized successfully :)")


def _parse_list_str(val: str | None) -> list[str]:
    """Parse a JSON list string into a Python list of strings."""
    if not val:
        return []
    try:
        data = json.loads(val)
        if isinstance(data, list):
            return [str(x).strip() for x in data if x is not None and str(x).strip()]
        return [str(data).strip()]
    except (json.JSONDecodeError, TypeError, ValueError):
        cleaned = str(val).strip()
        return [cleaned] if cleaned else []


def _format_str_val(val: str | list[str] | None) -> str | None:
    if val is None:
        return None
    if isinstance(val, list):
        items = [str(x).strip() for x in val if x is not None and str(x).strip()]
        return ", ".join(items) if items else None
    cleaned = str(val).strip()
    return cleaned if cleaned else None


def read_all_brand_names() -> list[str]:
    query = 'SELECT DISTINCT "openfda.brand_name" from final_dataset_cache WHERE "openfda.brand_name" IS NOT NULL'
    result = con.execute(query).fetchall()
    names = set()
    for row in result:
        for name in _parse_list_str(row[0]):
            if name:
                names.add(name)
    return sorted(names)


def read_all_generic_names() -> list[str]:
    query = 'SELECT DISTINCT "openfda.generic_name" from final_dataset_cache WHERE "openfda.generic_name" IS NOT NULL'
    result = con.execute(query).fetchall()
    names = set()
    for row in result:
        for name in _parse_list_str(row[0]):
            if name:
                names.add(name)
    return sorted(names)


def read_all_manufacturers(
    brand_name: str | None = None,
    generic_name: str | None = None,
) -> list[str]:
    conditions = ['"openfda.manufacturer_name" IS NOT NULL']
    params = []
    if brand_name:
        conditions.append('"openfda.brand_name" ILIKE ?')
        params.append(f"%{brand_name}%")
    if generic_name:
        conditions.append('"openfda.generic_name" ILIKE ?')
        params.append(f"%{generic_name}%")

    where_clause = " AND ".join(conditions)
    query = f'SELECT DISTINCT "openfda.manufacturer_name" from final_dataset_cache WHERE {where_clause}'
    result = con.execute(query, params).fetchall()
    manufacturers = set()
    for row in result:
        for m in _parse_list_str(row[0]):
            if m:
                manufacturers.add(m)
    return sorted(manufacturers)


def read_records(
    manufacturer: str | None = None,
    brand_name: str | None = None,
    generic_name: str | None = None,
    set_id: str | None = None,
) -> list[dict]:
    conditions = []
    params = []
    if set_id:
        conditions.append("set_id = ?")
        params.append(set_id)
    if manufacturer:
        conditions.append('"openfda.manufacturer_name" ILIKE ?')
        params.append(f"%{manufacturer}%")
    if brand_name:
        conditions.append('"openfda.brand_name" ILIKE ?')
        params.append(f"%{brand_name}%")
    if generic_name:
        conditions.append('"openfda.generic_name" ILIKE ?')
        params.append(f"%{generic_name}%")

    where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""
    query = f"""
    SELECT 
        set_id,
        id,
        version,
        effective_time,
        "openfda.brand_name",
        "openfda.generic_name",
        "openfda.manufacturer_name",
        "openfda.product_ndc",
        "openfda.package_ndc",
        "openfda.route",
        "openfda.product_type",
        dosage_forms_and_strengths
    from final_dataset_cache
    {where_clause}
    """
    rows = con.execute(query, params).fetchall()
    records = []
    for r in rows:
        routes = _parse_list_str(r[9])
        strengths = _parse_list_str(r[11])
        records.append(
            {
                "set_id": r[0],
                "id": r[1],
                "version": r[2],
                "effective_time": r[3],
                "dosage_forms_and_strengths": strengths,
                "openfda": {
                    "brand_name": _parse_list_str(r[4]),
                    "generic_name": _parse_list_str(r[5]),
                    "manufacturer_name": _parse_list_str(r[6]),
                    "product_ndc": _parse_list_str(r[7]),
                    "package_ndc": _parse_list_str(r[8]),
                    "route": routes,
                    "product_type": _parse_list_str(r[10]),
                    "dosage_form": routes,
                    "strength": strengths,
                },
            }
        )
    return records


def read_record_by_set_id(set_id: str) -> dict | None:
    records = read_records(set_id=set_id)
    return records[0] if records else None


def read_dosage_forms(records_or_ndcs: list[dict] | list[str]) -> list[str]:
    forms = set()
    for item in records_or_ndcs:
        if isinstance(item, dict):
            openfda = item.get("openfda", {})
            for route in openfda.get("route", []):
                if route:
                    forms.add(route)
            for df in openfda.get("dosage_form", []):
                if df:
                    forms.add(df)
        elif isinstance(item, str):
            query = 'SELECT DISTINCT "openfda.route" from final_dataset_cache WHERE "openfda.product_ndc" ILIKE ?'
            res = con.execute(query, [f"%{item}%"]).fetchall()
            for r in res:
                for route in _parse_list_str(r[0]):
                    if route:
                        forms.add(route)
    return sorted(forms)


def filter_records_by_dosage_form(records: list[dict], selected_form: str) -> list[dict]:
    if selected_form in ("All", "All Forms"):
        return records
    matched = []
    for rec in records:
        openfda = rec.get("openfda", {})
        routes = openfda.get("route", [])
        dosage_forms = openfda.get("dosage_form", [])
        strengths = rec.get("dosage_forms_and_strengths", [])
        if (
            selected_form in routes
            or selected_form in dosage_forms
            or any(selected_form.lower() in s.lower() for s in strengths)
        ):
            matched.append(rec)
    return matched or records


def add_tracked_drug(
    record: dict | str | list | None = None,
    set_id: str | None = None,
    option_name: str = "default_drug_info",
    option_ids: list[int] | None = None,
) -> int:
    if isinstance(record, list):
        pids = add_tracked_drugs(record, option_name=option_name)
        return pids[0] if pids else 0

    if isinstance(record, str) and set_id is None:
        set_id = record
        record = None

    if record is None and set_id is None:
        raise ValueError("Either record or set_id must be provided.")

    if record is None and set_id is not None:
        record = read_record_by_set_id(set_id)
        if not record:
            raise ValueError(f"No record found in dataset for set_id: {set_id}")

    target_set_id = (record.get("set_id") if isinstance(record, dict) else None) or set_id
    if not target_set_id:
        raise ValueError("Record does not have a valid set_id.")

    rec_dict = record if isinstance(record, dict) else {}
    openfda = rec_dict.get("openfda", {}) if isinstance(rec_dict.get("openfda"), dict) else {}

    brand_name = _format_str_val(openfda.get("brand_name") or rec_dict.get("brand_name"))
    generic_name = _format_str_val(openfda.get("generic_name") or rec_dict.get("generic_name"))
    manufacturer_name = _format_str_val(
        openfda.get("manufacturer_name")
        or rec_dict.get("manufacturer")
        or rec_dict.get("manufacturer_name")
    )
    dosage_form = _format_str_val(openfda.get("dosage_form") or rec_dict.get("dosage_form"))
    route = _format_str_val(openfda.get("route") or rec_dict.get("route"))
    product_type = _format_str_val(openfda.get("product_type") or rec_dict.get("product_type"))
    product_ndc = _format_str_val(openfda.get("product_ndc") or rec_dict.get("product_ndc"))
    package_ndc = _format_str_val(openfda.get("package_ndc") or rec_dict.get("package_ndc"))
    effective_time = _format_str_val(rec_dict.get("effective_time"))

    upsert_query = """    
    INSERT INTO tracked_drugs (
        set_id, brand_name, generic_name, manufacturer_name,
        dosage_form, route, product_type, product_ndc,
        package_ndc, effective_time
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT (set_id) DO NOTHING
    RETURNING product_id
    """
    res = con.execute(
        upsert_query,
        [
            target_set_id,
            brand_name,
            generic_name,
            manufacturer_name,
            dosage_form,
            route,
            product_type,
            product_ndc,
            package_ndc,
            effective_time,
        ],
    ).fetchone()
    if res is not None:
        product_id = res[0]
    else:
        existing = con.execute(
            "SELECT product_id FROM tracked_drugs WHERE set_id = ?",
            [target_set_id],
        ).fetchone()

        if existing is None:
            raise RuntimeError(f"Unable to find tracked drug: {target_set_id}")

        product_id = existing[0]
    if option_ids is not None:
        for oid in option_ids:
            link_drug_option(product_id=product_id, option_id=oid)
    elif option_name:
        # Fall back to name-based lookup (CLI flow)
        opt = get_option_by_name(option_name)
        if opt:
            link_drug_option(product_id=product_id, option_id=opt["id"])

    return product_id


def add_tracked_drugs(
    set_ids_or_records: list[str] | list[dict],
    option_name: str = "default_drug_info",
    option_ids: list[int] | None = None,
) -> list[int]:
    product_ids = []
    for item in set_ids_or_records:
        if isinstance(item, str):
            pid = add_tracked_drug(set_id=item, option_name=option_name, option_ids=option_ids)
            product_ids.append(pid)
        elif isinstance(item, dict):
            pid = add_tracked_drug(record=item, option_name=option_name, option_ids=option_ids)
            product_ids.append(pid)
    return product_ids


def remove_tracked_drug(
    set_id: str | None = None,
    product_id: int | None = None,
) -> bool:
    if set_id is None and product_id is None:
        raise ValueError("Either set_id or product_id must be provided.")

    if product_id is None and set_id is not None:
        row = con.execute(
            "SELECT product_id FROM tracked_drugs WHERE set_id = ?", [set_id]
        ).fetchone()
        if not row:
            return False
        product_id = row[0]

    con.execute("DELETE FROM options_drugs WHERE product_id = ?", [product_id])
    con.execute("DELETE FROM tracked_drugs WHERE product_id = ?", [product_id])
    return True


def read_tracked_drugs() -> list[dict]:
    query = """
    SELECT 
        d.product_id,
        d.set_id,
        d.brand_name,
        d.generic_name,
        d.manufacturer_name,
        d.dosage_form,
        d.route,
        d.product_type,
        d.product_ndc,
        d.package_ndc,
        d.effective_time,
        o.id AS option_id,
        o.name AS option_name,
        o.list_of_options
    FROM tracked_drugs d
    LEFT JOIN options_drugs od ON d.product_id = od.product_id
    LEFT JOIN options o ON od.option_id = o.id
    ORDER BY d.product_id ASC
    """
    rows = con.execute(query).fetchall()
    drugs_map = {}
    for r in rows:
        pid = r[0]
        if pid not in drugs_map:
            drugs_map[pid] = {
                "product_id": r[0],
                "set_id": r[1],
                "brand_name": r[2],
                "generic_name": r[3],
                "manufacturer_name": r[4],
                "dosage_form": r[5],
                "route": r[6],
                "product_type": r[7],
                "product_ndc": r[8],
                "package_ndc": r[9],
                "effective_time": r[10],
                "options": [],
                "monitored_sections": [],
            }
        if r[11] is not None:
            drugs_map[pid]["options"].append({"id": r[11], "name": r[12]})
            if r[13]:
                for sec in r[13]:
                    if sec not in drugs_map[pid]["monitored_sections"]:
                        drugs_map[pid]["monitored_sections"].append(sec)

    return list(drugs_map.values())


def get_tracked_drug(
    set_id: str | None = None,
    product_id: int | None = None,
) -> dict | None:
    if set_id is None and product_id is None:
        raise ValueError("Either set_id or product_id must be provided.")

    all_tracked = read_tracked_drugs()
    for drug in all_tracked:
        if set_id and drug["set_id"] == set_id:
            return drug
        if product_id and drug["product_id"] == product_id:
            return drug
    return None


def read_tracked_set_ids() -> list[str]:
    rows = con.execute("SELECT set_id FROM tracked_drugs WHERE set_id IS NOT NULL").fetchall()
    return [r[0] for r in rows if r[0]]


def is_drug_tracked(set_id: str) -> bool:
    row = con.execute("SELECT 1 FROM tracked_drugs WHERE set_id = ? LIMIT 1", [set_id]).fetchone()
    return row is not None


def read_all_options() -> list[dict]:
    rows = con.execute("SELECT id, name, list_of_options FROM options ORDER BY id ASC").fetchall()
    return [{"id": r[0], "name": r[1], "list_of_options": r[2]} for r in rows]


def get_option_by_name(name: str) -> dict | None:
    row = con.execute(
        "SELECT id, name, list_of_options FROM options WHERE name = ? LIMIT 1", [name]
    ).fetchone()
    if row:
        return {"id": row[0], "name": row[1], "list_of_options": row[2]}
    return None


def create_option(name: str, list_of_options: list[str]) -> int:
    existing = get_option_by_name(name)
    if existing:
        con.execute(
            "UPDATE options SET list_of_options = ? WHERE name = ?",
            [list_of_options, name],
        )
        return existing["id"]
    res = con.execute(
        "INSERT INTO options (name, list_of_options) VALUES (?, ?) RETURNING id",
        [name, list_of_options],
    ).fetchone()
    return res[0]


def link_drug_option(product_id: int, option_id: int) -> None:
    con.execute(
        "INSERT INTO options_drugs (option_id, product_id) VALUES (?, ?) ON CONFLICT (option_id, product_id) DO NOTHING",
        [option_id, product_id],
    )


def get_drug_monitored_sections(
    set_id: str | None = None,
    product_id: int | None = None,
) -> list[str]:
    drug = get_tracked_drug(set_id=set_id, product_id=product_id)
    if drug and drug.get("monitored_sections"):
        return drug["monitored_sections"]

    default_opt = get_option_by_name("default_drug_info")
    if default_opt and default_opt.get("list_of_options"):
        return default_opt["list_of_options"]

    return [
        "boxed_warning",
        "contraindications",
        "warnings_and_precautions",
        "warnings",
        "adverse_reactions",
        "drug_interactions",
    ]


def get_available_fields() -> list[str]:
    list_of_cols = (
        con.execute(f"""
        SELECT column_name 
        FROM (DESCRIBE SELECT * FROM '{csv_path}');
        """)
        .fetchnumpy()["column_name"]
        .tolist()
    )
    excluced_cols = [
        "openfda.application_number",
        "openfda.generic_name",
        "openfda.brand_name",
        "openfda.manufacturer_name",
        "openfda.product_ndc",
        "openfda.package_ndc",
        "openfda.route",
        "dosage_forms_and_strengths",
    ]
    list_of_cols = [col for col in list_of_cols if col not in excluced_cols]
    return list_of_cols
