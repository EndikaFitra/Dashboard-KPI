import logging
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("KPI Analytics API starting up...")
    from app.database import engine, Base
    import models.division      # noqa
    import models.kpi           # noqa
    import models.period        # noqa
    import models.mapping       # noqa
    import models.fact_raw      # noqa
    import models.fact_quarterly # noqa
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables ensured.")
    yield
    logger.info("KPI Analytics API shutting down.")


app = FastAPI(
    title="KPI Analytics API",
    version="1.0.0",
    description="Data Warehouse REST API for KPI Performance Monitoring",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from routers import dashboard, kpi, chatbot, mcp  # noqa

app.include_router(dashboard.router, prefix="/dashboard", tags=["Dashboard"])
app.include_router(kpi.router, prefix="/kpi", tags=["KPI"])
app.include_router(chatbot.router, prefix="/chatbot", tags=["Chatbot"])
app.include_router(mcp.router, prefix="/mcp", tags=["MCP"])


@app.get("/", tags=["Health"])
def health_check():
    return {"status": "ok", "service": "KPI Analytics API", "version": "1.0.0"}
