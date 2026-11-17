# Architecture

## Layers

| Layer | Folder | Holds | May import |
|---|---|---|---|
| Presentation | `legacy/streamlit/` (today), `frontend/` (planned React app) | Screens, session handling, styling | `backend`, `data_pipeline` |
| Application | `backend/app/` | The 16 stage services, the orchestrator, settings, file repositories | `data_pipeline` |
| Library | `data_pipeline/src/kg_pipeline/` | Models, connectors, type coercion, ontology drafting and validation, graph validation, traversal | nothing in this repo |

The library never imports the backend or a UI. The backend never imports Streamlit. This is what lets a React
frontend replace Streamlit without touching the pipeline.

## Where each stage lives

| Stages | Service package | Pure logic they call |
|---|---|---|
| 1-4 Prepare | `backend/app/services/sources/stages/` | `connectors/`, `metadata_extractor/key_detector.py` |
| 5-10 Ontology | `backend/app/services/ontology/stages/` | `ontology_compiler/compiler.py`, `validator.py`, `repositories/file/ontology_repository.py` |
| 11-16 Build | `backend/app/services/build/stages/` | `normalizer.py`, `id_generator.py`, `graph_builder/graph_validator.py`, `repositories/file/snapshot_store.py`, `loaders/neo4j_loader.py` |

Stages keep the shape `run(ctx, ...)`: they read earlier results from `PipelineContext`, write their own, and log.

## Not built yet (deliberately)

There is no API layer, authentication, PostgreSQL metadata store, Redis, background worker, or Cypher/NLP query yet.
Nothing in the current app needs them. When the API is added it goes in `backend/app/api/` and `backend/app/dto/`
and calls the same stage services the Streamlit pages call today.

## Known limits carried over from the prototype

- State is one `PipelineContext` per browser session, held in server memory.
- File stores have no locking, so they assume one writer.
- Stage 3 writes a single shared `storage/catalog/catalog.json`.
- Explorer PII hiding is a fixed list of column names, not the ontology's `pii` flag.
