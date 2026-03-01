import json
import random
import logging
from pathlib import Path
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent / "data"

_questions_cache: list[dict] | None = None


def _load_questions() -> list[dict]:
    global _questions_cache
    if _questions_cache is not None:
        return _questions_cache
    path = DATA_DIR / "quiz_questions.json"
    with open(path, "r", encoding="utf-8") as f:
        _questions_cache = json.load(f)
    return _questions_cache


app = Server("skillgraph-question-bank")


@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="get_questions",
            description="Get quiz questions for a specific concept",
            inputSchema={
                "type": "object",
                "properties": {
                    "concept_id": {
                        "type": "string",
                        "description": "The concept ID to get questions for",
                    },
                    "count": {
                        "type": "integer",
                        "description": "Number of questions to return",
                        "default": 2,
                    },
                },
                "required": ["concept_id"],
            },
        ),
        Tool(
            name="get_remediation_questions",
            description="Get practice questions targeting a specific error type for remediation",
            inputSchema={
                "type": "object",
                "properties": {
                    "concept_id": {
                        "type": "string",
                        "description": "The concept ID",
                    },
                    "error_type": {
                        "type": "string",
                        "enum": ["procedural", "conceptual", "transfer", "prerequisite_absence"],
                        "description": "The type of error to target",
                    },
                },
                "required": ["concept_id"],
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    questions = _load_questions()

    if name == "get_questions":
        concept_id = arguments["concept_id"]
        count = arguments.get("count", 2)
        matched = [q for q in questions if q["concept_id"] == concept_id]
        selected = random.sample(matched, min(count, len(matched))) if matched else []
        return [TextContent(type="text", text=json.dumps(selected, indent=2))]

    if name == "get_remediation_questions":
        concept_id = arguments["concept_id"]
        error_type = arguments.get("error_type", "conceptual")
        matched = [q for q in questions if q["concept_id"] == concept_id]
        targeted = []
        for q in matched:
            distractor_types = q.get("distractor_types", {})
            if error_type in distractor_types.values():
                targeted.append(q)
        result = targeted if targeted else matched[:2]
        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    return [TextContent(type="text", text=json.dumps({"error": f"Unknown tool: {name}"}))]


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
