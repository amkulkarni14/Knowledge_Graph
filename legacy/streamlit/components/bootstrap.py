"""Makes the backend and the pipeline library importable and keeps one PipelineContext per browser session."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
for _path in (ROOT / "data_pipeline" / "src", ROOT / "backend"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import streamlit as st  # noqa: E402

from app.domain.pipeline_context import PipelineContext  # noqa: E402


def get_ctx() -> PipelineContext:
    if "ctx" not in st.session_state:
        st.session_state["ctx"] = PipelineContext()
    return st.session_state["ctx"]


def reset_ctx() -> None:
    old = st.session_state.get("ctx")
    if old is not None and old.source is not None:
        try:
            old.source.close()
        except Exception:  # noqa: BLE001
            pass
    st.session_state["ctx"] = PipelineContext()
    for k in [k for k in st.session_state if k != "ctx"]:
        del st.session_state[k]
