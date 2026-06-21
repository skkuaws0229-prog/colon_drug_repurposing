from __future__ import annotations

import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

try:
    from api.routers.assistant import router as assistant_router
except Exception:
    try:
        from routes.assistant import router as assistant_router
    except Exception:
        from backend.routes.assistant import router as assistant_router

try:
    from routes.image_modal import router as image_modal_router
except Exception:
    from backend.routes.image_modal import router as image_modal_router
try:
    from routes.docking import router as docking_router
except Exception:
    from backend.routes.docking import router as docking_router
try:
    from routes.alphafold import router as alphafold_router
except Exception:
    from backend.routes.alphafold import router as alphafold_router
try:
    from api.literature_rag import router as literature_rag_router
except Exception:
    try:
        from backend.api.literature_rag import router as literature_rag_router
    except Exception:
        literature_rag_router = None

try:
    from api.routers.diseases import router as api_diseases_router
except Exception:
    api_diseases_router = None


# Ensure project root is importable when running from ~/drug-project/backend
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

app = FastAPI(title="Drug Project Backend API", version="0.5.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Keep existing graph route if available.
try:
    from routes.graph import router as graph_router

    app.include_router(graph_router)
except Exception:
    try:
        from backend.routes.graph import router as graph_router

        app.include_router(graph_router)
    except Exception:
        # Do not fail app startup if graph router is absent in certain deployments.
        pass

# Include assistant router exactly once.
app.include_router(assistant_router)
app.include_router(image_modal_router)
app.include_router(docking_router)
app.include_router(alphafold_router)
if literature_rag_router is not None:
    app.include_router(literature_rag_router)
if api_diseases_router is not None:
    app.include_router(api_diseases_router)


@app.get("/")
def root() -> dict[str, str]:
    return {"status": "ok", "service": "drug-project-backend", "docs": "/docs"}

