from typing import AsyncGenerator, Dict
from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI

from .models import create_db_and_tables
from .routers import binaries
from .routers import search


log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    await create_db_and_tables()

    yield


app = FastAPI(lifespan=lifespan)
app.include_router(binaries.router)
app.include_router(search.router)


@app.get("/")
def root() -> Dict:
    return {"message": "Hello, I'm Chacra!"}
