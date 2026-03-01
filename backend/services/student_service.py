import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import aiosqlite

from config import settings
from models.student import GapArea, StudentProfile

logger = logging.getLogger(__name__)

DB_PATH = settings.sqlite_db_path


async def init_db():
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS students (
                student_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                language_pref TEXT DEFAULT 'en',
                diagnostic_results TEXT DEFAULT '{}',
                gap_areas TEXT DEFAULT '[]',
                last_reinforced TEXT DEFAULT '{}',
                created_at TEXT NOT NULL
            )
            """
        )
        await db.commit()
    logger.info("SQLite database initialized at %s", DB_PATH)


async def create_profile(profile: StudentProfile) -> StudentProfile:
    if not profile.created_at:
        profile.created_at = datetime.now(timezone.utc).isoformat()

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT OR REPLACE INTO students
            (student_id, name, language_pref, diagnostic_results, gap_areas, last_reinforced, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                profile.student_id,
                profile.name,
                profile.language_pref,
                json.dumps(profile.diagnostic_results),
                json.dumps([g.model_dump() for g in profile.gap_areas]),
                json.dumps(profile.last_reinforced),
                profile.created_at,
            ),
        )
        await db.commit()
    return profile


async def get_profile(student_id: str) -> StudentProfile | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM students WHERE student_id = ?", (student_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if not row:
                return None
            return StudentProfile(
                student_id=row["student_id"],
                name=row["name"],
                language_pref=row["language_pref"],
                diagnostic_results=json.loads(row["diagnostic_results"]),
                gap_areas=[
                    GapArea(**g) for g in json.loads(row["gap_areas"])
                ],
                last_reinforced=json.loads(row["last_reinforced"]),
                created_at=row["created_at"],
            )


async def update_diagnostic_results(
    student_id: str,
    results: dict[str, float],
    gaps: list[GapArea],
) -> StudentProfile | None:
    profile = await get_profile(student_id)
    if not profile:
        return None

    profile.diagnostic_results = results
    profile.gap_areas = gaps
    return await create_profile(profile)


async def update_reinforcement(student_id: str, concept_id: str):
    profile = await get_profile(student_id)
    if not profile:
        return
    profile.last_reinforced[concept_id] = datetime.now(timezone.utc).isoformat()
    await create_profile(profile)
