#!/usr/bin/env python3
# -*- coding: utf-8 -*-


import os
import asyncio
from collections import defaultdict
from dotenv import load_dotenv
import discord
from discord import app_commands
from openai import OpenAI
from rag_module import RAG

# 讀取 .env
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
SYSTEM_PROMPT = os.getenv("SYSTEM_PROMPT", "You are a helpful assistant.")

# --- Discord Client 設定 ---
intents = discord.Intents.default()
intents.message_content = True # 需於 Portal 開啟 Message Content Intent
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)
rag = RAG()  # 若索引尚未建立，rag.index 會是 None


# 以頻道為單位保存簡易上下文（只保留最近 N 則）
CHANNEL_MEMORY_LIMIT = 6
history = defaultdict(list) # {channel_id: [(role, content), ...]}

# --- OpenAI Client ---
oi = OpenAI(api_key=OPENAI_API_KEY)


def call_openai(messages):
    """呼叫 OpenAI Responses API，messages 為 [{role, content}] 陣列。"""
    input_items = [
        {"role": "system", "content": SYSTEM_PROMPT},
    ] + messages

    resp = oi.responses.create(
        model=OPENAI_MODEL,
        input=input_items,
    )

    # 盡量取出文字（兼容不同 SDK 結構）
    try:
        return getattr(resp, "output_text", None) or "".join(
            block.text
            for item in (getattr(resp, "output", None) or [])
            for block in (getattr(item, "content", None) or [])
            if getattr(block, "text", None)
        )
    except Exception:
        text_chunks = []
        if getattr(resp, "output", None):
            for item in resp.output:
                if getattr(item, "content", None):
                    for c in item.content:
                        if getattr(c, "type", "") == "output_text" and getattr(c, "text", None):
                            text_chunks.append(c.text)
        return "".join(text_chunks) or "(No text returned)"


@tree.command(name="rag", description="Ask with Retrieval-Augmented Generation")
@app_commands.describe(query="你的問題（會從 docs 向量索引中檢索）")
async def rag_cmd(interaction: discord.Interaction, query: str):
    await interaction.response.defer(thinking=True)
    try:
        if getattr(rag, "X", None) is None or not getattr(rag, "meta", []):
            await interaction.followup.send(
                "RAG 索引尚未建立。請先把文件放到 ./docs，然後執行：\n`python rag_index.py`"
            )
            return

        answer = await rag.answer(query)
        await interaction.followup.send(answer[:1900] or "（沒有產生結果）")
    except Exception as e:
        await interaction.followup.send(f"RAG 出錯：{e}")


# --- 工具：加入記憶並裁切 ---

def remember_and_trim(channel_id: int, role: str, content: str):
    hist = history[channel_id]
    hist.append({"role": role, "content": content})
    # 只保留最近 CHANNEL_MEMORY_LIMIT*2（user/assistant 成對）
    if len(hist) > CHANNEL_MEMORY_LIMIT * 2:
        history[channel_id] = hist[-CHANNEL_MEMORY_LIMIT * 2 :]

# --- 事件：Bot 啟動 ---
@client.event
async def on_ready():
    try:
        await tree.sync()
        print(f"Logged in as {client.user} (ID: {client.user.id})")
    except Exception as e:
        print("Slash commands sync failed:", e)

# --- 斜線指令：/ask ---
@tree.command(name="ask", description="向 AI 詢問問題")
async def ask(interaction: discord.Interaction, question: str):
    await interaction.response.defer(thinking=True)

    channel_id = interaction.channel_id
    remember_and_trim(channel_id, "user", question)

    # 準備對話內容
    msgs = history[channel_id]
    answer = await asyncio.get_event_loop().run_in_executor(None, lambda: call_openai(msgs))
    remember_and_trim(channel_id, "assistant", answer)
    await interaction.followup.send(answer[:1900])  # Discord 單則訊息長度限制 ~2000

# --- 一般訊息觸發（@機器人 或私訊）---
@client.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    # 私訊或被提及才回
    mentioned = client.user in message.mentions if client.user else False
    if not (isinstance(message.channel, discord.DMChannel) or mentioned):
        return

    async with message.channel.typing():
        channel_id = message.channel.id
        user_text = message.content.replace(f"<@{client.user.id}>", "").strip() if client.user else message.content
        if not user_text:
            user_text = "嗨～需要我做什麼？可以輸入 /ask 試試看唷！"
            await message.reply(user_text)
            return

        remember_and_trim(channel_id, "user", user_text)
        msgs = history[channel_id]
        answer = await asyncio.get_event_loop().run_in_executor(None, lambda: call_openai(msgs))
        remember_and_trim(channel_id, "assistant", answer)
        await message.reply(answer[:1900])


if __name__ == "__main__":
    if not DISCORD_TOKEN or not OPENAI_API_KEY:
        raise RuntimeError("請先設定 .env 裡的 DISCORD_TOKEN 與 OPENAI_API_KEY")
    client.run(DISCORD_TOKEN)