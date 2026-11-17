"""The 16 pipeline stages in order, grouped in three parts. Shared by the stages, the orchestrator and every UI."""
from __future__ import annotations

STAGES: list[dict] = [
    # part A - prepare
    {"no": 1, "key": "scope", "title": "Goal & Scope", "part": "A", "icon": "🎯"},
    {"no": 2, "key": "connect", "title": "Connect Safely", "part": "A", "icon": "🔌"},
    {"no": 3, "key": "schema", "title": "Schema Extraction", "part": "A", "icon": "🗂️"},
    {"no": 4, "key": "analysis", "title": "Schema Analysis", "part": "A", "icon": "🔍"},
    # part B - ontology
    {"no": 5, "key": "manual", "title": "Manual Ontology", "part": "B", "icon": "✍️"},
    {"no": 6, "key": "ai", "title": "Groq AI Suggestions", "part": "B", "icon": "🤖"},
    {"no": 7, "key": "review", "title": "Review & Approve", "part": "B", "icon": "✅"},
    {"no": 8, "key": "validate", "title": "Ontology Validation", "part": "B", "icon": "🧪"},
    {"no": 9, "key": "repo", "title": "Ontology Versioning", "part": "B", "icon": "🗃️"},
    {"no": 10, "key": "plan", "title": "Build Plan", "part": "B", "icon": "🗺️"},
    # part C - build
    {"no": 11, "key": "extract", "title": "Data Extraction", "part": "C", "icon": "📥"},
    {"no": 12, "key": "quality", "title": "Data Quality", "part": "C", "icon": "🩺"},
    {"no": 13, "key": "clean", "title": "Clean & Entity Resolution", "part": "C", "icon": "🧹"},
    {"no": 14, "key": "build", "title": "Build NetworkX Graph", "part": "C", "icon": "🕸️"},
    {"no": 15, "key": "gvalidate", "title": "Graph Validation", "part": "C", "icon": "🛡️"},
    {"no": 16, "key": "store", "title": "Store Graph", "part": "C", "icon": "💾"},
]
PARTS = {"A": "Prepare", "B": "Ontology (rulebook)", "C": "Build the graph"}
