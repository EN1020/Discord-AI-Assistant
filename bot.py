#!/usr/bin/env python3
from __future__ import annotations

import logging

import discord
from discord import app_commands

from discord_ai_bot.config import load_settings
from discord_ai_bot.discord_utils import (
    append_sources,
    interaction_key,
    message_key,
    split_discord_message,
    strip_bot_mentions,
)
from discord_ai_bot.indexing import build_index
from discord_ai_bot.memory import ConversationMemory
from discord_ai_bot.openai_service import OpenAIResponder, OpenAIServiceError
from discord_ai_bot.rag import RAG

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("discord-ai-bot")

settings = load_settings()
settings.validate_runtime()

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)
memory = ConversationMemory(max_messages=settings.memory_messages)
responder = OpenAIResponder(settings)
rag = RAG(settings)
startup_checked = False


@client.event
async def on_ready() -> None:
    global startup_checked
    try:
        if not startup_checked:
            startup_checked = True
            await _maybe_build_rag_on_start()
        await tree.sync()
        logger.info("Logged in as %s (ID: %s)", client.user, client.user.id if client.user else "?")
    except Exception:
        logger.exception("Slash commands sync failed")


@tree.command(name="ask", description="向 AI 詢問問題，可自動使用網路搜尋")
@app_commands.describe(question="你的問題")
async def ask(interaction: discord.Interaction, question: str) -> None:
    await _answer_with_openai(interaction, question, force_web=False)


@tree.command(name="web", description="強制使用網路搜尋回答最新資訊")
@app_commands.describe(question="需要查網路的問題")
async def web(interaction: discord.Interaction, question: str) -> None:
    await _answer_with_openai(interaction, question, force_web=True)


@tree.command(name="rag", description="從本地 docs/RAG 知識庫回答")
@app_commands.describe(query="你的問題")
async def rag_cmd(interaction: discord.Interaction, query: str) -> None:
    await interaction.response.defer(thinking=True)
    key = interaction_key(interaction)
    history = memory.snapshot(key)

    if not rag.ready():
        await interaction.followup.send(
            "RAG 索引尚未建立。請先把文件放到 `./docs`，然後執行：\n`python rag_index.py`"
        )
        return

    try:
        answer = await rag.answer(query, history=history)
    except Exception:
        logger.exception("RAG command failed")
        await interaction.followup.send("RAG 查詢失敗，請稍後再試或查看伺服器 log。")
        return

    memory.add_user(key, query)
    memory.add_assistant(key, answer)
    await _send_interaction_text(interaction, answer)


@tree.command(name="sources", description="查看本地 RAG 最相關來源")
@app_commands.describe(query="要搜尋本地知識庫的問題")
async def sources(interaction: discord.Interaction, query: str) -> None:
    await interaction.response.defer(thinking=True, ephemeral=True)
    if not rag.ready():
        await interaction.followup.send("RAG 索引尚未建立。")
        return
    try:
        hits = await rag.search(query, k=settings.rag_top_k)
    except Exception:
        logger.exception("RAG sources lookup failed")
        await interaction.followup.send("來源查詢失敗。")
        return
    if not hits:
        await interaction.followup.send("沒有找到本地來源。")
        return
    lines = ["Top local sources:"]
    for index, hit in enumerate(hits, start=1):
        path = hit.get("path") or hit.get("source") or hit.get("id")
        question = hit.get("question") or ""
        lines.append(f"{index}. score={hit['score']:.2f} - {path} {question}")
    await interaction.followup.send("\n".join(lines)[: settings.discord_message_limit])


@tree.command(name="summarize", description="摘要你和機器人的近期對話")
async def summarize(interaction: discord.Interaction) -> None:
    await interaction.response.defer(thinking=True, ephemeral=True)
    key = interaction_key(interaction)
    transcript = memory.transcript(key)
    if not transcript:
        await interaction.followup.send("目前沒有可摘要的近期對話。")
        return
    prompt = "請用繁體中文摘要以下對話，列出重點與待辦：\n\n" + transcript
    try:
        result = await responder.answer(prompt, history=[], force_web=False)
    except OpenAIServiceError:
        logger.exception("Summarize failed")
        await interaction.followup.send("摘要失敗，請稍後再試。")
        return
    await _send_interaction_text(interaction, result.text)


@tree.command(name="forget", description="清除你在此頻道的對話記憶")
async def forget(interaction: discord.Interaction) -> None:
    memory.clear(interaction_key(interaction))
    await interaction.response.send_message("已清除你在此頻道的對話記憶。", ephemeral=True)


@tree.command(name="reload_rag", description="重新載入已建立的 RAG 索引")
@app_commands.checks.has_permissions(manage_guild=True)
async def reload_rag(interaction: discord.Interaction) -> None:
    rag.reload()
    status = "已重新載入 RAG 索引。" if rag.ready() else "找不到 RAG 索引，請先執行 `python rag_index.py`。"
    await interaction.response.send_message(status, ephemeral=True)


@reload_rag.error
async def reload_rag_error(interaction: discord.Interaction, error: app_commands.AppCommandError) -> None:
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message("這個指令需要 Manage Server 權限。", ephemeral=True)
        return
    logger.error("reload_rag command error", exc_info=error)
    await interaction.response.send_message("重新載入失敗。", ephemeral=True)


@client.event
async def on_message(message: discord.Message) -> None:
    if message.author.bot:
        return

    mentioned = client.user in message.mentions if client.user else False
    if not (isinstance(message.channel, discord.DMChannel) or mentioned):
        return

    question = strip_bot_mentions(message.content, client.user.id if client.user else None)
    if not question:
        await message.reply("嗨，需要我做什麼？可以用 `/ask`、`/rag` 或 `/web` 問我。")
        return

    async with message.channel.typing():
        key = message_key(message)
        history = memory.snapshot(key)
        try:
            result = await responder.answer(question, history=history, force_web=False)
        except OpenAIServiceError:
            logger.exception("Message answer failed")
            await message.reply("我剛剛連 OpenAI 時失敗了，請稍後再試。")
            return

        answer = append_sources(result.text, result.sources)
        memory.add_user(key, question)
        memory.add_assistant(key, answer)
        await _send_message_text(message, answer)


async def _answer_with_openai(
    interaction: discord.Interaction,
    question: str,
    force_web: bool,
) -> None:
    await interaction.response.defer(thinking=True)
    key = interaction_key(interaction)
    history = memory.snapshot(key)
    try:
        result = await responder.answer(question, history=history, force_web=force_web)
    except OpenAIServiceError:
        logger.exception("OpenAI answer failed")
        await interaction.followup.send("我剛剛連 OpenAI 時失敗了，請稍後再試。")
        return

    answer = append_sources(result.text, result.sources)
    memory.add_user(key, question)
    memory.add_assistant(key, answer)
    await _send_interaction_text(interaction, answer)


async def _send_interaction_text(interaction: discord.Interaction, text: str) -> None:
    for chunk in split_discord_message(text, settings.discord_message_limit):
        await interaction.followup.send(chunk)


async def _send_message_text(message: discord.Message, text: str) -> None:
    chunks = split_discord_message(text, settings.discord_message_limit)
    await message.reply(chunks[0])
    for chunk in chunks[1:]:
        await message.channel.send(chunk)


async def _maybe_build_rag_on_start() -> None:
    if rag.ready() or not settings.auto_build_rag_on_start:
        return
    logger.info("RAG index missing; AUTO_BUILD_RAG_ON_START is enabled")
    count = await build_index(settings)
    rag.reload()
    logger.info("RAG startup build completed with %s records", count)


if __name__ == "__main__":
    client.run(settings.discord_token)
