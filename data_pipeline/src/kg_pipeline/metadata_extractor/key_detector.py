"""Schema analysis rules (no I/O): classify tables and find relationship candidates, including undeclared FKs.

Pure functions over a SchemaCatalog; Stage 4 calls them and records the result."""
from __future__ import annotations

from kg_pipeline.models.ontology_models import DataType
from kg_pipeline.models.schema_models import SchemaCatalog, TableInfo


def classify_with_reason(t: TableInfo, catalog: SchemaCatalog) -> tuple[str, str]:
    fk_cols = {c for fk in t.foreign_keys for c in fk.columns}
    pk = set(t.primary_key)
    has_date = any(c.data_type in (DataType.DATE, DataType.DATETIME) and c.name not in ("updated_at", "created_at")
                   for c in t.columns.values())
    if len(t.foreign_keys) >= 2 and pk and pk <= fk_cols:
        return "bridge", "primary key is made of foreign keys"
    if not pk:
        return "log", "no primary key"
    if (t.row_estimate or 0) > 5_000_000 and has_date:
        return "log", "very large, date-based"
    if len(t.columns) <= 3 and catalog.referenced_by(t.name):
        return "lookup", "small code table referenced by others"
    if has_date:
        return "event", "own key and a business date"
    return "entity", "own key and descriptive columns"


def classify_table(t: TableInfo, catalog: SchemaCatalog) -> str:
    """The table type only (entity / event / bridge / lookup / log)."""
    return classify_with_reason(t, catalog)[0]


def undeclared_fk_candidates(t: TableInfo, catalog: SchemaCatalog) -> list[dict]:
    """Columns named like another table's single-column PK but with no declared FK."""
    fk_cols = {c for fk in t.foreign_keys for c in fk.columns}
    pk_owner = {o.primary_key[0]: o.name for o in catalog.tables.values() if len(o.primary_key) == 1}
    out = []
    for col in t.columns:
        if col in fk_cols or col in t.primary_key:
            continue
        target = pk_owner.get(col)
        if target and target != t.name:
            out.append({"table": t.name, "column": col, "probably_references": target})
    return out


def relationship_candidates(catalog: SchemaCatalog, analysis: list[dict]) -> list[dict]:
    """Candidate edges implied by declared FKs, bridges and undeclared FK candidates."""
    kinds = {a["table"]: a["type"] for a in analysis}
    out = []
    for t in catalog.tables.values():
        if kinds.get(t.name) == "bridge":
            a, b = t.foreign_keys[0], t.foreign_keys[1]
            out.append({"from": a.ref_table, "to": b.ref_table, "via": t.name, "pattern": "M:N bridge",
                        "edge properties": [c for c in t.columns if c not in t.primary_key]})
            continue
        for fk in t.foreign_keys:
            pattern = "self reference" if fk.ref_table == t.name else "N:1 foreign key"
            out.append({"from": t.name, "to": fk.ref_table, "via": f"{t.name}.{','.join(fk.columns)}",
                        "pattern": pattern, "edge properties": []})
    for a in analysis:
        for c in a["undeclared_fk"]:
            out.append({"from": c["table"], "to": c["probably_references"], "via": f"{c['table']}.{c['column']}",
                        "pattern": "undeclared FK (verify in Stage 12)", "edge properties": []})
    return out
