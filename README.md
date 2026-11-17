# Enterprise Knowledge Graph Studio (prototype)

PostgreSQL tables **or several uploaded CSV files** → hybrid ontology (manual / rule-drafted + Groq AI,
human-approved, versioned) → NetworkX `MultiDiGraph` → validation gate → versioned graph store
(JSON + GraphML, optional Neo4j).
Every stage has its own module **and** its own screen that shows what it does, why, its input,
its output and what actually happened.

## Run

```powershell
python -m venv .venv ; .venv\Scripts\activate
pip install -r requirements.txt

# Legacy Streamlit UI (run from its folder so .streamlit/config.toml is picked up)
cd legacy\streamlit
streamlit run streamlit_app.py

# Headless, same code as the UI (from the project root)
python scripts/run_pipeline.py              # built-in sample data + offline AI response
python scripts/run_pipeline.py --postgres   # PG* variables from .env (read-only user)
python scripts/run_pipeline.py --use-groq   # live Groq call (GROQ_API_KEY)
python scripts/run_pipeline.py --csv-dir data/samples/customer360   # every .csv in a folder, ontology drafted by rules

# Tests (200): CSV source, ontology drafting, all 16 stages on files, the Streamlit screens, the CLI
pip install -r requirements-dev.txt
python -m pytest                            # from the project root; pytest.ini finds all three test folders
```

To try a real database: `psql -d retail -f database/postgres/seed/01_source_schema.sql`, copy `.env.example` to
`.env`, fill the `PG*` values, then choose **PostgreSQL** in Stage 2.

To try files: Stage 2 → **Upload CSV files** → select several files at once (or use the bundled Customer 360
examples), then Stage 5 → **🪄 Draft from the schema**. See [Uploading CSV files](#uploading-csv-files-stage-2).

## Folder structure

```
enterprices_kg/
├── backend/                         application layer: stages, config, file stores. No UI. Depends on data_pipeline.
│   ├── app/
│   │   ├── core/                    config.py (settings from env), stage_registry.py (the 16 stages in 3 parts)
│   │   ├── domain/                  pipeline_context.py (stage hand-off + activity log)
│   │   ├── services/
│   │   │   ├── sources/stages/      Part A   s01_scope … s04_schema_analysis
│   │   │   ├── ontology/stages/     Part B   s05_manual_ontology … s10_build_plan
│   │   │   └── build/               Part C   stages/ s11_extraction … s16_graph_persistence; orchestrator.py (run_all)
│   │   └── repositories/file/       ontology_repository.py (versions + audit), snapshot_store.py (graph snapshots, CURRENT)
│   └── tests/                       test_pipeline_csv.py (all stages on files, CLI)
├── data_pipeline/                   pure library: no web framework, no UI, no import from backend
│   ├── src/kg_pipeline/
│   │   ├── models/                  ontology_models, schema_models, naming
│   │   ├── preprocessing/           normalizer.py; connectors/ (csv_source, postgres_source, sample_source, sample_data, base)
│   │   ├── metadata_extractor/      key_detector.py (table kinds, undeclared FKs, relationship candidates)
│   │   ├── ontology_compiler/       compiler.py (rule-based draft), validator.py (ontology validation)
│   │   ├── graph_builder/           id_generator.py, graph_validator.py, loaders/neo4j_loader.py
│   │   └── graph_algorithms/        traversal.py (neighbourhood, shortest connection), centrality.py
│   └── tests/                       test_csv_source, test_naming, test_ontology_draft
├── legacy/streamlit/                the current UI, kept until the React frontend replaces it
│   ├── streamlit_app.py             entry point (not named app.py: that would shadow backend/app)
│   ├── .streamlit/config.toml       UI theme
│   ├── components/                  bootstrap (session context), layout, graph_view, viz (PyVis)
│   ├── pages/                       home.py, s01_scope.py … s16_store.py, explorer.py (one screen per stage)
│   └── tests/test_ui.py             drives the real Streamlit app screen by screen
├── frontend/                        React app: folder scaffold only, no code yet (see frontend/README.md)
├── database/postgres/               seed/01_source_schema.sql (sample source), init/02_kg_meta_schema.sql (kg_meta DDL)
├── data/                            ontologies/, fixtures/ (recorded AI answer), samples/ (CSV examples)
├── scripts/run_pipeline.py          CLI runner
├── docs/architecture.md             layers and dependency rules
├── storage/                         runtime output (git-ignored)
│   ├── catalog/                     schema catalog (Stage 3)
│   ├── ontology_repo/<id>/          ontology versions vNNNN.json + audit.jsonl (Stage 9)
│   ├── graphs/<id>/<build_id>/      graph snapshots + CURRENT pointer (Stage 16)
│   └── logs/ai_requests.jsonl       every AI request (Stage 6)
├── conftest.py, pytest.ini          shared test setup and import paths
└── requirements.txt, requirements-dev.txt, .env.example
```

Dependency direction: `legacy/streamlit` (and later `frontend` via an API) → `backend` → `data_pipeline`. Never the other way.

Folders that exist as an empty scaffold (each holds only a `.gitkeep`; they follow the target skeleton and are filled as
features are built): `.github/workflows`, `docker/`, `backend/migrations`, most of `backend/app` beyond the stage services
(`api/`, `dto/`, `entities/`, `security/`, `workers/`, `database/`, `exceptions/`, …), `backend/tests/{unit,integration,contract}`,
`frontend/src/*`, `database/neo4j`, `contracts/`, `docs/decisions`.

## The stages

| # | Stage | Output |
|---|---|---|
| 1 | Goal & scope | scope sheet (questions, tables, sensitive columns) |
| 2 | Connect safely | read-only session (statement timeout, pool) **or** several uploaded CSV files as in-memory tables |
| 3 | Schema extraction | SchemaCatalog from `pg_catalog` |
| 4 | Schema analysis | table types, relationship candidates, undeclared FKs |
| 5 | Manual ontology | draft: classes, attributes, relationships, mapping (hand-made, or **🪄 drafted from the schema by rules**) |
| 6 | Groq AI suggestions | labelled suggestions (valid / needs review / invalid) |
| 7 | Review & approve | hybrid draft (origin manual / ai / hybrid) |
| 8 | Ontology validation | structural + semantic report |
| 9 | Ontology versioning | approved immutable version (four-eyes), audit, rollback |
| 10 | Build plan | table/column → node/edge mapping |
| 11 | Data extraction | keyset batches, checkpoints, watermarks |
| 12 | Data quality | block / quarantine / warn findings, referential integrity |
| 13 | Clean & entity resolution | canonical records, merges, quarantine |
| 14 | Build NetworkX graph | `MultiDiGraph` (nodes pass, edges pass) |
| 15 | Graph validation | reconciliation + ontology conformance |
| 16 | Store graph | versioned snapshot, CURRENT pointer, optional Neo4j |

On the sample data the result is 33 nodes and 52 edges: customer 11 is merged into customer 2,
product 206 (negative price) and the PLACED edge of order 1012 (customer 99 does not exist) are
quarantined with reasons, and Customer:7 is reported as isolated.

## Uploading CSV files (Stage 2)

Stage 2 → **Upload CSV files** takes several files at once. Each file becomes a table `csv.<file_name>`; everything
after Stage 2 runs unchanged because the files sit behind the same read-only `DataSource` interface as PostgreSQL.
On the 7 bundled Customer 360 files the whole pipeline gives **54 nodes and 64 edges**, in any file order.

What is worked out from the files (rules only, no AI), and shown in Stage 2 with every doubt listed as a warning:

| Step | Rule |
|---|---|
| Parse | UTF-8 (BOM) or Windows-1252; delimiter `, ; tab \|` read from the header; blank lines skipped; `""`, `null`, `none`, `nan`, `n/a` are NULL |
| Names | `Cust ID` → column `cust_id` (the original header is kept and shown in Stage 3); file name → table / class name |
| Types | bigint, double precision (also `4,500,000`), boolean `true/false`, date `YYYY-MM-DD`, timestamp; everything else text. Phone / account numbers, codes and numbers with leading zeros stay text |
| Key | an identifier column (`id`, `code`, `no`…) whose values are unique; else a composite such as `cust_id + score_date`; else a unique text column. A failing identifier (repeats, empty cells) is **reported, never replaced** by another column |
| Links | a column named like another file's key whose values match it becomes a foreign key (same name + overlap, or "mentions the file name" + ≥80 % overlap, flagged *values only*). Orphan values are reported and later set aside by Stage 12 |

Stage 5 → **🪄 Draft from the schema** then builds the ontology: a class per table that has a key, `Owner -[HAS_HOLDER]-> Holder`
per link (via the holder's rows), `A -[BRIDGE]-> B` per bridge table, and notes for everything it had to skip. The draft goes
through the same validation (Stage 8), four-eyes approval (Stage 9) and build (Stages 10-16) as a hand-made ontology.
The same button works for PostgreSQL schemas.

Safety: files live in memory only (never written to disk); limits `KG_MAX_UPLOAD_FILES` (25), `KG_MAX_UPLOAD_MB` (25 per file) and
`KG_MAX_UPLOAD_ROWS` (200 000 per file); only `.csv/.tsv/.txt`, binary files refused, file names reduced to a safe table name,
cells that start with `= + - @` are reported and kept as text. **All files are checked before anything is loaded** — if one is bad
the upload is rejected with every reason and the previous connection stays as it was.

Things to know: the AI step (Stage 6) is optional for files — the recorded offline answer only fits the built-in sample, so with files it
needs a live Groq key or is skipped. Cleaning in Stage 13 handles spacing, case and merging of records; messy number or date formats
(`₹ 45,00,000`, `12/03/1985`, `8.5%`) must be fixed in the file — they are reported as warnings and kept as text.
`data/samples/customer360_messy` shows this: it is refused because its identifiers repeat.

## Design rules

* The builder never hard-codes a table or class; everything comes from the approved ontology.
* The AI only suggests: it sees structure (and optional masked samples, never PII), every
  suggestion is checked against the real schema, and a person decides. Builds never call the AI.
* Only an approved ontology version can be built; approval needs a passing validation and a
  reviewer different from the author.
* A graph becomes CURRENT only if Stage 15 passes. Bad rows are quarantined with a reason, never dropped.
* Table and column names reach SQL only after a catalog whitelist check and `psycopg.sql.Identifier` quoting.

## Not in this prototype yet

Incremental (watermark) graph updates and CDC, DuckDB "Silver" staging for very large tables,
moving the ontology repository from files into `kg_meta` in PostgreSQL, analytics / GraphRAG /
NL queries, authentication and role-based PII hiding.
