import asyncio
import os
import sys

from config import settings
from services.neo4j_service import Neo4jService

async def test():
    n = Neo4jService()
    try:
        await n.connect()
        print("Success")
    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test())
