import json
import os
from typing import Any

import requests
from dotenv import load_dotenv
from neo4j import GraphDatabase


load_dotenv()


# -----------------------------
# DB CONNECTION
# -----------------------------
def get_driver():
    return GraphDatabase.driver(
        os.getenv("NEO4J_URI"),
        auth=(os.getenv("NEO4J_USERNAME"), os.getenv("NEO4J_PASSWORD"))
    )



# -----------------------------
# NODE EXISTS
# -----------------------------
def node_exists(label: str) -> bool:
    driver = get_driver()

    try:
        with driver.session() as session:
            return session.run("""
                MATCH (n)
                RETURN any(l IN labels(n) WHERE l = $label) AS exists
            """, label=label).single()["exists"]
    finally:
        driver.close()



def _to_iso_date(dmy: str | None) -> str | None:
    """Convert DD/MM/YYYY -> YYYY-MM-DD for Neo4j date()."""
    if not dmy:
        return None
    parts = dmy.split("/")
    if len(parts) != 3:
        return None
    dd, mm, yyyy = parts
    return f"{yyyy}-{mm}-{dd}"


# -----------------------------
# Active substances ETL
# -----------------------------
def fetch_substances_subset() -> list[dict[str, Any]]:
    """
    Fetch active substances from the SANTE endpoint and return selected fields.
    """
    url = (
        "https://api.datalake.sante.service.ec.europa.eu/"
        "sante/pesticides/active-substances-download"
    )
    params = {"format": "json", "api-version": "v3.0"}
    headers = {"Accept": "application/x-ndjson, application/json"}

    resp = requests.get(url, params=params, headers=headers, timeout=60)
    print("Substances URL:", resp.url)
    resp.raise_for_status()

    content_type = resp.headers.get("Content-Type", "").lower()
    if "ndjson" in content_type:
        raw_records = [json.loads(line) for line in resp.text.splitlines() if line.strip()]
    elif "application/json" in content_type:
        body = resp.json()
        raw_records = body if isinstance(body, list) else [body]
    else:
        raise ValueError(f"Unsupported Content-Type: {content_type}")

    substances: list[dict[str, Any]] = []
    for r in raw_records:
        substances.append(
            {
                "substance_name": r.get("substance_name"),
                "as_cas_number": r.get("as_cas_number"),
                "substance_status": r.get("substance_status"),
                "substance_category": r.get("substance_category"),
                "approval_date": _to_iso_date(r.get("approval_date")),
                "expiry_date": _to_iso_date(r.get("expiry_date")),
                "risk_assessment": r.get("risk_assessment"),
                "classification_reg_1272": r.get("classification_reg_1272"),
                "basic_substance": r.get("basic_substance"),
                "low_risk_active_substance": r.get("low_risk_active_substance"),
                "candidate_for_substitution": r.get("candidate_for_substitution"),
                "candidate_for_substitution_type": r.get("candidate_for_substitution_type"),
            }
        )

    return substances


def insert_substances_in_batches(
    substances: list[dict[str, Any]],
    batch_size: int = 50,
) -> int:
    """
    Insert/update :Chemical nodes in Neo4j.
    """
    neo4j_uri = os.getenv("NEO4J_URI")
    neo4j_user = os.getenv("NEO4J_USERNAME")
    neo4j_password = os.getenv("NEO4J_PASSWORD")
    if not neo4j_uri or not neo4j_user or not neo4j_password:
        raise ValueError("Missing NEO4J_URI / NEO4J_USERNAME / NEO4J_PASSWORD")

    query = """
    UNWIND $batch AS row
    WITH row
    WHERE row.as_cas_number IS NOT NULL AND trim(row.as_cas_number) <> ""
    MERGE (c:Chemical {cas_number: row.as_cas_number})
    SET
      c.active_substance = row.substance_name,
      c.status = row.substance_status,
      c.category = row.substance_category,
      c.approval_date = CASE WHEN row.approval_date IS NOT NULL THEN date(row.approval_date) ELSE NULL END,
      c.expiry_date = CASE WHEN row.expiry_date IS NOT NULL THEN date(row.expiry_date) ELSE NULL END,
      c.risk_assessment = row.risk_assessment,
      c.classification = row.classification_reg_1272,
      c.basic_substance = (row.basic_substance = "Yes"),
      c.low_risk = (row.low_risk_active_substance = "Yes"),
      c.candidate_for_substitution = (row.candidate_for_substitution = "Yes"),
      c.substitution_type = row.candidate_for_substitution_type
    RETURN count(*) AS processed_rows
    """

    total_processed = 0
    driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
    try:
        with driver.session() as session:
            for i in range(0, len(substances), batch_size):
                batch = substances[i : i + batch_size]
                result = session.run(query, batch=batch)
                processed = result.single()["processed_rows"]
                total_processed += processed
                print(f"Processed Chemical batch {i // batch_size + 1}: {processed} rows")
    finally:
        driver.close()

    return total_processed


# -----------------------------
# Residue levels ETL
# -----------------------------
def fetch_residue_levels() -> list[dict[str, Any]]:
    """
    Fetch ALL pesticide residue records (all languages) using `nextLink` pagination.
    """
    url = "https://api.datalake.sante.service.ec.europa.eu/sante/pesticides/pesticide-residues"
    params = {"format": "json", "api-version": "v3.0"}
    headers = {"Accept": "application/json"}

    all_raw: list[dict[str, Any]] = []
    next_url: str | None = url
    next_params: dict[str, str] | None = params
    page = 0

    while next_url:
        resp = requests.get(next_url, params=next_params, headers=headers, timeout=60)
        resp.raise_for_status()
        body = resp.json()

        raw = body.get("value", []) if isinstance(body, dict) else body
        all_raw.extend(raw)

        page += 1
        print(f"Fetched residues page {page}: {len(raw)} (total={len(all_raw)})")

        next_url = body.get("nextLink") if isinstance(body, dict) else None
        next_params = None  # nextLink already contains params

    levels: list[dict[str, Any]] = []
    for r in all_raw:
        residue_id = r.get("pesticide_residue_id")
        residue_name = r.get("pesticide_residue_name")
        if residue_id is None or not residue_name:
            continue

        levels.append(
            {
                "residue_id": str(int(residue_id)),
                "residue_name": residue_name,
                "language": r.get("pesticide_residue_lg"),
                "footnote_code": r.get("pesticide_residue_footnote_code"),
                "footnote_def": r.get("pesticide_residue_footnote_def"),
                "footnote_text": r.get("pesticide_residue_footnote_txt"),
                "version": r.get("pesticide_residue_version_nbr"),
                "original_residue_id": (
                    str(int(r["original_pesticide_residue_id"]))
                    if r.get("original_pesticide_residue_id") is not None
                    else None
                ),
            }
        )

    print(f"Total residue records kept: {len(levels)}")
    return levels


def insert_residue_levels_in_batches(
    residue_levels: list[dict[str, Any]],
    batch_size: int = 200,
) -> int:
    """
    Insert/update :ResidueLevel nodes in Neo4j.
    """
    neo4j_uri = os.getenv("NEO4J_URI")
    neo4j_user = os.getenv("NEO4J_USERNAME")
    neo4j_password = os.getenv("NEO4J_PASSWORD")
    if not neo4j_uri or not neo4j_user or not neo4j_password:
        raise ValueError("Missing NEO4J_URI / NEO4J_USERNAME / NEO4J_PASSWORD")

    query = """
    UNWIND $batch AS row
    MERGE (r:ResidueLevel {residue_id: row.residue_id})
    SET
      r.residue_name = row.residue_name,
      r.language = row.language,
      r.footnote_code = row.footnote_code,
      r.footnote_def = row.footnote_def,
      r.footnote_text = row.footnote_text,
      r.version = row.version,
      r.original_residue_id = row.original_residue_id
    RETURN count(*) AS processed_rows
    """

    total_processed = 0
    driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
    try:
        with driver.session() as session:
            for i in range(0, len(residue_levels), batch_size):
                batch = residue_levels[i : i + batch_size]
                result = session.run(query, batch=batch)
                processed = result.single()["processed_rows"]
                total_processed += processed
                print(f"Processed ResidueLevel batch {i // batch_size + 1}: {processed} rows")
    finally:
        driver.close()

    return total_processed



def parse_response(resp: requests.Response) -> tuple[list[dict[str, Any]], str | None]:
    """
    Handles both JSON and NDJSON responses returned by the SANTE API.
    """
    content_type = resp.headers.get("Content-Type", "").lower()
    text = resp.text.strip()

    if "ndjson" in content_type or "\n{" in text:
        records = [json.loads(line) for line in text.splitlines() if line.strip()]
        return records, None

    try:
        body = resp.json()
    except json.JSONDecodeError:
        records = [json.loads(line) for line in text.splitlines() if line.strip()]
        return records, None

    if isinstance(body, dict):
        return body.get("value", []), body.get("nextLink")

    if isinstance(body, list):
        return body, None

    return [], None


# -----------------------------
# MRL download ETL
# -----------------------------
def fetch_mrl_download(language_code: str = "EN") -> list[dict[str, Any]]:
    """
    Fetch ALL MRL download records using `nextLink` pagination.
    Supports both JSON and NDJSON responses.
    """
    url = "https://api.datalake.sante.service.ec.europa.eu/sante/pesticides/pesticide-residues-mrls-download"

    params = {
        "language_code": language_code,
        "format": "json",
        "api-version": "v3.0",
    }

    headers = {"Accept": "application/json, application/x-ndjson"}

    all_raw: list[dict[str, Any]] = []
    next_url: str | None = url
    next_params: dict[str, str] | None = params
    page = 0

    while next_url:
        resp = requests.get(
            next_url,
            params=next_params,
            headers=headers,
            timeout=90,
        )
        resp.raise_for_status()

        records, next_link = parse_response(resp)

        all_raw.extend(records)

        page += 1
        print(f"Fetched MRL page {page}: {len(records)} (total={len(all_raw)})")

        next_url = next_link
        next_params = None  # nextLink already contains params

    print(f"Total MRL raw records: {len(all_raw)}")
    return all_raw

def _pick(d: dict[str, Any], *keys: str) -> Any:
    for k in keys:
        if k in d and d[k] is not None:
            return d[k]
    return None


def transform_mrl_records(raw_records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Normalize MRL records to stable schema for Neo4j insert.
    """
    out: list[dict[str, Any]] = []

    for r in raw_records:
        residue_id = _pick(r, "pesticide_residue_id", "residue_id")
        product_id = _pick(r, "product_id")
        mrl_value = _pick(r, "pesticide_residue_mrl", "mrl", "mrl_value")
        unit = _pick(r, "mrl_unit", "unit")
        mrl_id = _pick(r, "pesticide_residue_mrl_id", "mrl_id")

        if residue_id is None or product_id is None:
            continue

        out.append(
            {
                "mrl_id": str(int(mrl_id)) if mrl_id is not None else f"{int(residue_id)}::{int(product_id)}",
                "residue_id": str(int(residue_id)),
                "product_id": str(int(product_id)),
                "mrl_value": mrl_value,
                "unit": unit,
                "product_name": _pick(r, "product_name"),
                "product_code": _pick(r, "product_code"),
                "language": _pick(r, "language_code", "language"),
                "note": _pick(r, "remark", "notes", "comment"),
                "source_regulation": _pick(r, "legislation", "regulation"),
                "version": _pick(r, "version", "pesticide_residue_version_nbr"),
            }
        )

    print(f"Transformed MRL records kept: {len(out)}")
    return out


def insert_mrls_in_batches(
    mrl_records: list[dict[str, Any]],
    batch_size: int = 500,
) -> int:
    """
    Insert MRL facts and relationships:
      (r:ResidueLevel)-[:HAS_MRL]->(m:MRL)-[:FOR_PRODUCT]->(p:Product)
    """
    neo4j_uri = os.getenv("NEO4J_URI")
    neo4j_user = os.getenv("NEO4J_USERNAME")
    neo4j_password = os.getenv("NEO4J_PASSWORD")
    if not neo4j_uri or not neo4j_user or not neo4j_password:
        raise ValueError("Missing NEO4J_URI / NEO4J_USERNAME / NEO4J_PASSWORD")

    query = """
    UNWIND $batch AS row

    MERGE (r:ResidueLevel {residue_id: row.residue_id})

    MERGE (p:Product {product_id: row.product_id})
    SET
      p.product_name = coalesce(row.product_name, p.product_name),
      p.product_code = coalesce(row.product_code, p.product_code)

    MERGE (m:MRL {mrl_id: row.mrl_id})
    SET
      m.residue_id = row.residue_id,
      m.product_id = row.product_id,
      m.mrl_value = row.mrl_value,
      m.unit = row.unit,
      m.language = row.language,
      m.note = row.note,
      m.source_regulation = row.source_regulation,
      m.version = row.version

    MERGE (r)-[:HAS_MRL]->(m)
    MERGE (m)-[:FOR_PRODUCT]->(p)

    RETURN count(*) AS processed_rows
    """

    total_processed = 0
    driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
    try:
        with driver.session() as session:
            for i in range(0, len(mrl_records), batch_size):
                batch = mrl_records[i : i + batch_size]
                result = session.run(query, batch=batch)
                processed = result.single()["processed_rows"]
                total_processed += processed
                print(f"Processed MRL batch {i // batch_size + 1}: {processed} rows")
    finally:
        driver.close()

    return total_processed





# -----------------------------
# FETCH PRODUCTS
# -----------------------------
def fetch_products():
    url = "https://api.datalake.sante.service.ec.europa.eu/sante/pesticides/pesticide-residues-products"
    params = {"api-version": "v3.0", "language": "EN", "format": "json"}

    all_raw = []
    next_url = url
    next_params = params

    while next_url:
        resp = requests.get(next_url, params=next_params)
        print("Products URL:", resp.url)

        resp.raise_for_status()

        records, next_link = parse_response(resp)
        all_raw.extend(records)

        next_url = next_link
        next_params = None

    return all_raw


# -----------------------------
# FETCH MRL (PER PRODUCT ✅)
# -----------------------------
def fetch_product_current_mrl_all_residues(product_ids: list[str]) -> list[dict[str, Any]]:
    url = "https://api.datalake.sante.service.ec.europa.eu/sante/pesticides/product-current-mrl-all-residues"

    headers = {"Accept": "application/json"}
    all_raw = []

    for pid in product_ids:
        params = {
            "api-version": "v3.0",
            "format": "json",
            "PRODUCT_ID": pid
        }

        resp = requests.get(url, params=params, headers=headers)

        print(f"Fetching MRL for PRODUCT_ID={pid}")

        if resp.status_code != 200:
            print("❌ Failed:", resp.text)
            continue

        records, _ = parse_response(resp)
        all_raw.extend(records)

    print(f"✅ Total MRL records fetched: {len(all_raw)}")
    return all_raw



# -----------------------------
# PRODUCTS TRANSFORM
# -----------------------------
def transform_products(raw_products: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for r in raw_products:
        pid = _pick(r, "product_id")
        if pid is None:
            continue

        out.append(
            {
                "product_id": str(int(pid)),
                "product_name": _pick(r, "product_name"),
                "product_code": _pick(r, "product_code"),
                "language": _pick(r, "language"),
                "parent_product_id": (
                    str(int(_pick(r, "product_parent_id")))
                    if _pick(r, "product_parent_id") is not None
                    else None
                ),
            }
        )

    print(f"✅ Transformed products: {len(out)}")
    return out


# -----------------------------
# PRODUCTS INSERT (WITH HIERARCHY)
# -----------------------------
def insert_products_in_batches(products: list[dict[str, Any]], batch_size: int = 500) -> int:
    query = """
    UNWIND $batch AS row

    MERGE (p:Product {product_id: row.product_id})
    SET
      p.product_name = row.product_name,
      p.product_code = row.product_code,
      p.language = row.language,
      p.parent_product_id = row.parent_product_id

    WITH p, row

    FOREACH (_ IN CASE WHEN row.parent_product_id IS NOT NULL THEN [1] ELSE [] END |
        MERGE (parent:Product {product_id: row.parent_product_id})
        MERGE (p)-[:BELONGS_TO]->(parent)
    )

    RETURN count(*) AS processed_rows
    """

    total = 0
    driver = get_driver()

    try:
        with driver.session() as session:
            for i in range(0, len(products), batch_size):
                batch = products[i:i + batch_size]
                result = session.run(query, batch=batch)
                total += result.single()["processed_rows"]
                print(f"Processed Product batch {i//batch_size+1}")
    finally:
        driver.close()

    return total


def node_exists(label: str) -> bool:
    driver = get_driver()

    try:
        with driver.session() as session:
            return session.run("""
                MATCH (n)
                RETURN any(l IN labels(n) WHERE l = $label) AS exists
            """, label=label).single()["exists"]
    finally:
        driver.close()



if __name__ == "__main__":
    # ------------------------------------------------------------
    # 1) Active substances load (DISABLED - already created)
    # ------------------------------------------------------------
    # substances = fetch_substances_subset()
    # print(f"Fetched {len(substances)} substances")
    # total_substances = insert_substances_in_batches(substances=substances, batch_size=50)
    # print(f"✅ Total Chemical nodes processed: {total_substances}")

    # ------------------------------------------------------------
    # 2) Residue levels load (DISABLED - already created)
    # ------------------------------------------------------------
    # residue_levels = fetch_residue_levels()
    # if residue_levels:
    #     print("First residue level:", residue_levels[0])
    # total_residue_levels = insert_residue_levels_in_batches(residue_levels=residue_levels, batch_size=200)
    # print(f"✅ Total ResidueLevel nodes processed: {total_residue_levels}")

    # ------------------------------------------------------------
    # 3) MRL download load (EN) - ENABLED
    # ------------------------------------------------------------
    
    
    if not node_exists("Product"):
        print("🚀 Loading Products...")
        raw_products = fetch_products()
        products = transform_products(raw_products)
        insert_products_in_batches(products)
    else:
        print("⏭ Products exist")

    
    
    mrl_raw = fetch_mrl_download(language_code="EN")
    if mrl_raw:
        print("First raw MRL record:", mrl_raw[0])

    mrl_records = transform_mrl_records(mrl_raw)
    if mrl_records:
        print("First transformed MRL record:", mrl_records[0])

    total_mrl = insert_mrls_in_batches(mrl_records=mrl_records, batch_size=500)
    print(f"✅ Total MRL records processed: {total_mrl}")