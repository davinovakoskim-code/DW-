from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app import models  # noqa: F401 - imports model metadata for table creation
from app.api.routes.chamados import router as chamados_router
from app.api.routes.jira import router as jira_router
from app.core.config import settings
from app.core.database import Base, engine
from app.services.sqlite_migration_service import migrar_sqlite_schema


STATIC_DIR = Path(__file__).resolve().parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    # For the prototype, tables are created automatically on startup.
    Base.metadata.create_all(bind=engine)
    migrar_sqlite_schema(engine)
    yield


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="Prototype API for DWPLUS ticket triage with local IA analysis.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "ok", "app": settings.app_name, "env": settings.app_env}


@app.get("/", include_in_schema=False)
def frontend():
    return FileResponse(STATIC_DIR / "index.html")


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.include_router(jira_router)
app.include_router(chamados_router)
