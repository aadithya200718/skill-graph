import json
import logging
from pathlib import Path

from neo4j import AsyncGraphDatabase, AsyncDriver

from config import settings
from models.concept import ConceptNode, PrerequisiteEdge

logger = logging.getLogger(__name__)


class Neo4jService:
    def __init__(self):
        self._driver: AsyncDriver | None = None

    async def connect(self):
        self._driver = AsyncGraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password),
        )
        try:
            await self._driver.verify_connectivity()
            logger.info("Connected to Neo4j at %s", settings.neo4j_uri)
        except Exception as exc:
            logger.error("Neo4j connection failed: %s", exc)
            self._driver = None
            raise

    async def close(self):
        if self._driver:
            await self._driver.close()

    async def check_health(self) -> bool:
        if not self._driver:
            return False
        try:
            await self._driver.verify_connectivity()
            return True
        except Exception:
            return False

    async def seed_graph(
        self, concepts: list[dict], edges: list[dict]
    ) -> dict[str, int]:
        if not self._driver:
            raise RuntimeError("Neo4j driver not initialized")

        async with self._driver.session() as session:
            await session.run("MATCH (n) DETACH DELETE n")

            for concept in concepts:
                await session.run(
                    """
                    CREATE (c:Concept {
                        concept_id: $concept_id,
                        name: $name,
                        description: $description,
                        semester: $semester,
                        subject: $subject,
                        difficulty: $difficulty,
                        category: $category,
                        estimated_hours: $estimated_hours
                    })
                    """,
                    **concept,
                )

            for edge in edges:
                await session.run(
                    """
                    MATCH (a:Concept {concept_id: $from_concept})
                    MATCH (b:Concept {concept_id: $to_concept})
                    CREATE (a)-[:REQUIRES {
                        strength: $strength,
                        description: $description
                    }]->(b)
                    """,
                    **edge,
                )

        logger.info(
            "Seeded %d concepts and %d edges", len(concepts), len(edges)
        )
        return {"concepts": len(concepts), "edges": len(edges)}

    async def get_concept(self, concept_id: str) -> ConceptNode | None:
        if not self._driver:
            return None
        async with self._driver.session() as session:
            result = await session.run(
                "MATCH (c:Concept {concept_id: $concept_id}) RETURN c",
                concept_id=concept_id,
            )
            record = await result.single()
            if record:
                node = record["c"]
                return ConceptNode(**dict(node))
        return None

    async def get_all_concepts(self) -> list[ConceptNode]:
        if not self._driver:
            return []
        async with self._driver.session() as session:
            result = await session.run("MATCH (c:Concept) RETURN c ORDER BY c.semester, c.name")
            records = await result.data()
            return [ConceptNode(**dict(r["c"])) for r in records]

    async def get_prerequisites(
        self, concept_id: str, depth: int = 3
    ) -> list[ConceptNode]:
        if not self._driver:
            return []
        query = f"""
            MATCH (c:Concept {{concept_id: $concept_id}})-[:REQUIRES*1..{depth}]->(prereq:Concept)
            RETURN DISTINCT prereq
        """
        async with self._driver.session() as session:
            result = await session.run(query, concept_id=concept_id)
            records = await result.data()
            return [ConceptNode(**dict(r["prereq"])) for r in records]

    async def find_root_causes(
        self, gap_ids: list[str]
    ) -> dict[str, list[str]]:
        if not self._driver:
            return {}

        root_causes: dict[str, list[str]] = {}
        async with self._driver.session() as session:
            for gap_id in gap_ids:
                result = await session.run(
                    """
                    MATCH path = (gap:Concept {concept_id: $gap_id})-[:REQUIRES*1..5]->(root:Concept)
                    WHERE NOT (root)-[:REQUIRES]->()
                    RETURN [node IN nodes(path) | node.concept_id] AS chain
                    ORDER BY length(path) DESC
                    LIMIT 1
                    """,
                    gap_id=gap_id,
                )
                record = await result.single()
                if record:
                    root_causes[gap_id] = record["chain"]
                else:
                    root_causes[gap_id] = [gap_id]

        return root_causes

    async def count_dependents(self, concept_id: str) -> int:
        if not self._driver:
            return 0
        async with self._driver.session() as session:
            result = await session.run(
                """
                MATCH (dependent:Concept)-[:REQUIRES*1..5]->(c:Concept {concept_id: $concept_id})
                RETURN count(DISTINCT dependent) AS count
                """,
                concept_id=concept_id,
            )
            record = await result.single()
            return record["count"] if record else 0

    async def get_visualization_data(
        self, gap_ids: list[str] | None = None
    ) -> dict:
        if not self._driver:
            return {"nodes": [], "edges": []}

        gap_set = set(gap_ids) if gap_ids else set()

        async with self._driver.session() as session:
            node_result = await session.run(
                "MATCH (c:Concept) RETURN c"
            )
            node_records = await node_result.data()

            edge_result = await session.run(
                """
                MATCH (a:Concept)-[r:REQUIRES]->(b:Concept)
                RETURN a.concept_id AS source, b.concept_id AS target,
                       r.strength AS strength, r.description AS description
                """
            )
            edge_records = await edge_result.data()

        nodes = []
        for r in node_records:
            c = dict(r["c"])
            state = "gap" if c["concept_id"] in gap_set else "unassessed"
            nodes.append({
                "id": c["concept_id"],
                "label": c["name"],
                "semester": c["semester"],
                "subject": c["subject"],
                "category": c["category"],
                "difficulty": c["difficulty"],
                "estimated_hours": c["estimated_hours"],
                "state": state,
            })

        edges = []
        for r in edge_records:
            edges.append({
                "source": r["source"],
                "target": r["target"],
                "strength": r["strength"],
                "description": r["description"],
            })

        return {"nodes": nodes, "edges": edges, "gap_nodes": list(gap_set)}


async def seed_from_files(neo4j_service: Neo4jService) -> dict[str, int]:
    data_dir = Path(__file__).parent.parent / "data"

    concepts_path = data_dir / "concepts.json"
    edges_path = data_dir / "prerequisites.json"

    if not concepts_path.exists() or not edges_path.exists():
        logger.warning("Data files not found in %s, skipping seed", data_dir)
        return {"concepts": 0, "edges": 0}

    with open(concepts_path, "r", encoding="utf-8") as f:
        concepts = json.load(f)

    with open(edges_path, "r", encoding="utf-8") as f:
        edges = json.load(f)

    return await neo4j_service.seed_graph(concepts, edges)
