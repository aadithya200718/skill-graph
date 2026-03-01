import json
import logging
from pathlib import Path
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent / "data"

_syllabus_cache: dict | None = None
_concepts_cache: list[dict] | None = None


def _load_syllabus() -> dict:
    global _syllabus_cache
    if _syllabus_cache is not None:
        return _syllabus_cache
    path = DATA_DIR / "syllabus.json"
    with open(path, "r", encoding="utf-8") as f:
        _syllabus_cache = json.load(f)
    return _syllabus_cache


def _load_concepts() -> list[dict]:
    global _concepts_cache
    if _concepts_cache is not None:
        return _concepts_cache
    path = DATA_DIR / "concepts.json"
    with open(path, "r", encoding="utf-8") as f:
        _concepts_cache = json.load(f)
    return _concepts_cache


app = Server("skillgraph-syllabus-db")


@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="get_syllabus",
            description="Get the list of concept IDs for a subject and semester",
            inputSchema={
                "type": "object",
                "properties": {
                    "subject": {
                        "type": "string",
                        "description": "Subject name (e.g., 'Machine Learning')",
                    },
                    "semester": {
                        "type": "integer",
                        "description": "Semester number (1-8)",
                    },
                },
                "required": ["subject"],
            },
        ),
        Tool(
            name="get_concept_details",
            description="Get full details for a concept by its ID",
            inputSchema={
                "type": "object",
                "properties": {
                    "concept_id": {
                        "type": "string",
                        "description": "The concept ID to look up",
                    },
                },
                "required": ["concept_id"],
            },
        ),
        Tool(
            name="list_subjects",
            description="List all available subjects in the syllabus",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    if name == "get_syllabus":
        syllabus = _load_syllabus()
        subject = arguments["subject"]
        semester = arguments.get("semester")

        subject_data = syllabus.get(subject)
        if not subject_data:
            return [TextContent(type="text", text=json.dumps({"error": f"Subject not found: {subject}", "available": list(syllabus.keys())}))]

        if semester is not None:
            sem_key = str(semester)
            concepts = subject_data.get(sem_key, [])
            return [TextContent(type="text", text=json.dumps({"subject": subject, "semester": semester, "concepts": concepts}))]

        all_concepts = {}
        for sem, concepts in subject_data.items():
            all_concepts[f"semester_{sem}"] = concepts
        return [TextContent(type="text", text=json.dumps({"subject": subject, "semesters": all_concepts}))]

    if name == "get_concept_details":
        concept_id = arguments["concept_id"]
        concepts = _load_concepts()
        for c in concepts:
            if c["concept_id"] == concept_id:
                return [TextContent(type="text", text=json.dumps(c, indent=2))]
        return [TextContent(type="text", text=json.dumps({"error": f"Concept not found: {concept_id}"}))]

    if name == "list_subjects":
        syllabus = _load_syllabus()
        subjects = []
        for subj, semesters in syllabus.items():
            total = sum(len(v) for v in semesters.values())
            subjects.append({"name": subj, "semesters": list(semesters.keys()), "concept_count": total})
        return [TextContent(type="text", text=json.dumps(subjects, indent=2))]

    return [TextContent(type="text", text=json.dumps({"error": f"Unknown tool: {name}"}))]


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
