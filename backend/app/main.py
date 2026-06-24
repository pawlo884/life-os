from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.config import settings
from app.database import Base, engine
import app.models  # noqa: F401 — ensure all tables register before create_all
from app.routers import api, books


@asynccontextmanager
async def lifespan(_: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.execute(text("ALTER TABLE books ADD COLUMN IF NOT EXISTS cover_url VARCHAR(512)"))
    yield
    await engine.dispose()


app = FastAPI(title="Life OS API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api.router, prefix="/api/v1")
app.include_router(books.router, prefix="/api/v1")


@app.get("/health")
async def health():
    return {"status": "ok"}
