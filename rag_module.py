"""Backward-compatible import wrapper for the RAG runtime."""

from discord_ai_bot.rag import RAG, RetrievedContext, _l2_normalize

__all__ = ["RAG", "RetrievedContext", "_l2_normalize"]
