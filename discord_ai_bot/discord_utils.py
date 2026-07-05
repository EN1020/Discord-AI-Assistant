from __future__ import annotations

from discord import Interaction, Message

from .memory import ConversationKey
from .openai_utils import Source


def interaction_key(interaction: Interaction) -> ConversationKey:
    guild_id = interaction.guild_id or 0
    channel_id = interaction.channel_id or 0
    return ConversationKey(guild_id=guild_id, channel_id=channel_id, user_id=interaction.user.id)


def message_key(message: Message) -> ConversationKey:
    guild_id = message.guild.id if message.guild else 0
    return ConversationKey(guild_id=guild_id, channel_id=message.channel.id, user_id=message.author.id)


def strip_bot_mentions(content: str, bot_id: int | None) -> str:
    if bot_id is None:
        return content.strip()
    return (
        content.replace(f"<@{bot_id}>", "")
        .replace(f"<@!{bot_id}>", "")
        .strip()
    )


def split_discord_message(text: str, limit: int = 1900) -> list[str]:
    if not text:
        return ["(No text returned)"]
    chunks: list[str] = []
    remaining = text.strip()
    while len(remaining) > limit:
        cut = remaining.rfind("\n", 0, limit)
        if cut < limit // 2:
            cut = remaining.rfind(" ", 0, limit)
        if cut < limit // 2:
            cut = limit
        chunks.append(remaining[:cut].strip())
        remaining = remaining[cut:].strip()
    if remaining:
        chunks.append(remaining)
    return chunks


def format_sources(sources: list[Source], max_sources: int = 5) -> str:
    if not sources:
        return ""
    lines = ["", "Sources:"]
    for index, source in enumerate(sources[:max_sources], start=1):
        lines.append(f"{index}. {source.title} - {source.url}")
    return "\n".join(lines)


def append_sources(text: str, sources: list[Source], max_sources: int = 5) -> str:
    suffix = format_sources(sources, max_sources=max_sources)
    return f"{text.strip()}{suffix}" if suffix else text.strip()
