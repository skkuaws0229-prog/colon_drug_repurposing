from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.core.config import get_settings
from api.routers.assistant import router as assistant_router
from backend.routes.alphafold import router as alphafold_router
from backend.routes.docking import router as docking_router
from api.routers.diseases import router as diseases_router
from api.routers.graph import router as graph_router
from api.routers.health import router as health_router
from api.routers.image_modal import router as image_modal_router


settings = get_settings()

app = FastAPI(title="Multi-Cancer Evidence API", version="0.4.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(diseases_router)
app.include_router(graph_router)
app.include_router(image_modal_router)
app.include_router(docking_router)
app.include_router(alphafold_router)
app.include_router(assistant_router)


@app.get("/")
def root() -> dict[str, object]:
    return {
        "status": "ok",
        "service": "drug-project-api",
        "docs": "/docs",
        "health": "/api/health",
        "db_health": "/api/db/health",
        "diseases": "/api/diseases",
        "candidate_example": "/api/diseases/LUAD/candidates",
        "graph_example": "/api/graph/LUAD",
        "graph_summary_example": "/api/graph/LUAD/summary",
    }
