import json
import asyncio
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class McpClient:
    def __init__(self, server_script: str):
        self._script = Path(server_script).resolve()
        self._process: asyncio.subprocess.Process | None = None
        self._request_id = 0

    async def _ensure_connected(self):
        if self._process is not None and self._process.returncode is None:
            return
        self._process = await asyncio.create_subprocess_exec(
            "python", str(self._script),
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

    async def call_tool(self, name: str, arguments: dict, timeout: float = 5.0) -> list[dict]:
        try:
            await self._ensure_connected()
        except Exception as exc:
            logger.warning("MCP server connection failed for %s: %s", self._script.name, exc)
            return []

        self._request_id += 1
        request = {
            "jsonrpc": "2.0",
            "id": self._request_id,
            "method": "tools/call",
            "params": {"name": name, "arguments": arguments},
        }

        try:
            msg = json.dumps(request) + "\n"
            self._process.stdin.write(msg.encode())
            await self._process.stdin.drain()

            raw = await asyncio.wait_for(
                self._process.stdout.readline(),
                timeout=timeout,
            )
            if not raw:
                return []

            response = json.loads(raw.decode())
            content = response.get("result", {}).get("content", [])
            results = []
            for item in content:
                if item.get("type") == "text":
                    try:
                        results.append(json.loads(item["text"]))
                    except json.JSONDecodeError:
                        results.append({"raw": item["text"]})
            return results

        except asyncio.TimeoutError:
            logger.warning("MCP tool call timed out: %s(%s)", name, arguments)
            return []
        except Exception as exc:
            logger.warning("MCP tool call failed: %s(%s): %s", name, arguments, exc)
            return []

    async def close(self):
        if self._process and self._process.returncode is None:
            self._process.terminate()
            try:
                await asyncio.wait_for(self._process.wait(), timeout=2.0)
            except asyncio.TimeoutError:
                self._process.kill()


class McpManager:
    def __init__(self):
        mcp_dir = Path(__file__).parent.parent / "mcp_servers"
        self.question_bank = McpClient(str(mcp_dir / "question_bank.py"))
        self.syllabus_db = McpClient(str(mcp_dir / "syllabus_db.py"))
        self._fallback_loaded = False
        self._fallback_questions: list[dict] = []

    def _load_fallback_questions(self) -> list[dict]:
        if self._fallback_loaded:
            return self._fallback_questions
        path = Path(__file__).parent.parent / "data" / "quiz_questions.json"
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                self._fallback_questions = json.load(f)
        self._fallback_loaded = True
        return self._fallback_questions

    async def get_questions(self, concept_id: str, count: int = 2) -> list[dict]:
        results = await self.question_bank.call_tool(
            "get_questions",
            {"concept_id": concept_id, "count": count},
        )
        if results:
            return results[0] if isinstance(results[0], list) else results

        fallback = self._load_fallback_questions()
        matched = [q for q in fallback if q.get("concept_id") == concept_id]
        import random
        return random.sample(matched, min(count, len(matched))) if matched else []

    async def get_remediation_questions(self, concept_id: str, error_type: str = "conceptual") -> list[dict]:
        results = await self.question_bank.call_tool(
            "get_remediation_questions",
            {"concept_id": concept_id, "error_type": error_type},
        )
        if results:
            return results[0] if isinstance(results[0], list) else results
        return await self.get_questions(concept_id, 2)

    async def get_syllabus(self, subject: str, semester: int | None = None) -> dict:
        args: dict[str, Any] = {"subject": subject}
        if semester is not None:
            args["semester"] = semester
        results = await self.syllabus_db.call_tool("get_syllabus", args)
        if results:
            return results[0] if isinstance(results[0], dict) else {}
        return {}

    async def close(self):
        await self.question_bank.close()
        await self.syllabus_db.close()


mcp_manager = McpManager()
