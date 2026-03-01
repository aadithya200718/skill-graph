import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from services.neo4j_service import Neo4jService, seed_from_files
from services import student_service
from services.mcp_client import mcp_manager
from services.hybrid_rag import HybridRAG
from agents.diagnostic_agent import DiagnosticAgent
from agents.pathway_agent import PathwayAgent
from agents.content_agent import ContentAgent

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)

_neo4j_service: Neo4jService | None = None
_diagnostic_agent: DiagnosticAgent | None = None
_pathway_agent: PathwayAgent | None = None
_content_agent: ContentAgent | None = None
_hybrid_rag: HybridRAG | None = None


def get_neo4j_service() -> Neo4jService:
    if _neo4j_service is None:
        raise RuntimeError("Neo4j service not initialized")
    return _neo4j_service


def get_diagnostic_agent() -> DiagnosticAgent | None:
    return _diagnostic_agent


def get_pathway_agent() -> PathwayAgent | None:
    return _pathway_agent


def get_content_agent() -> ContentAgent | None:
    return _content_agent


def get_hybrid_rag() -> HybridRAG | None:
    return _hybrid_rag


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _neo4j_service, _diagnostic_agent, _pathway_agent, _content_agent, _hybrid_rag

    await student_service.init_db()
    logger.info("SQLite database initialized")

    _neo4j_service = Neo4jService()
    try:
        await _neo4j_service.connect()
        result = await seed_from_files(_neo4j_service)
        logger.info("Graph seeded: %s", result)
    except Exception as exc:
        logger.error("Neo4j setup failed: %s", exc)
        logger.info("Continuing without Neo4j. Some features will be unavailable.")

    _diagnostic_agent = DiagnosticAgent(_neo4j_service)
    _pathway_agent = PathwayAgent(_neo4j_service)
    _content_agent = ContentAgent(_neo4j_service)
    _hybrid_rag = HybridRAG(_neo4j_service)
    logger.info("All agents initialized (MCP, RAG ready)")

    yield

    await mcp_manager.close()
    if _neo4j_service:
        await _neo4j_service.close()
    logger.info("Shutdown complete")


app = FastAPI(
    title="SkillGraph API",
    description="AI-powered diagnostic learning platform with knowledge graph gap analysis",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from routers import quiz_router, graph_router, remediation_router, agent_router, demo_router, decay_router, search_router

app.include_router(quiz_router.router)
app.include_router(graph_router.router)
app.include_router(remediation_router.router)
app.include_router(agent_router.router)
app.include_router(demo_router.router)
app.include_router(decay_router.router)
app.include_router(search_router.router)


@app.get("/api/v1/health")
async def health_check():
    neo4j_ok = False
    if _neo4j_service:
        neo4j_ok = await _neo4j_service.check_health()

    return {
        "status": "ok",
        "neo4j": "connected" if neo4j_ok else "disconnected",
        "agents": [
            a.model_dump()
            for a in (
                __import__("agents.agent_registry", fromlist=["registry"]).registry.get_all_cards()
            )
        ],
    }
