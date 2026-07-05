#!/usr/bin/env python3
"""Build the local RAG index from files in docs/."""

import asyncio

from discord_ai_bot.indexing import main


if __name__ == "__main__":
    asyncio.run(main())
