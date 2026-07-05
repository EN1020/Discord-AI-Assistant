from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import DefaultDict, Iterable, Literal, NamedTuple

Role = Literal["user", "assistant"]


class ConversationKey(NamedTuple):
    guild_id: int
    channel_id: int
    user_id: int


@dataclass(frozen=True)
class MemoryMessage:
    role: Role
    content: str

    def as_openai_message(self) -> dict[str, str]:
        return {"role": self.role, "content": self.content}


class ConversationMemory:
    def __init__(self, max_messages: int = 16):
        self.max_messages = max(2, max_messages)
        self._items: DefaultDict[ConversationKey, list[MemoryMessage]] = defaultdict(list)

    def add(self, key: ConversationKey, role: Role, content: str) -> None:
        if not content.strip():
            return
        items = self._items[key]
        items.append(MemoryMessage(role=role, content=content.strip()))
        if len(items) > self.max_messages:
            self._items[key] = items[-self.max_messages :]

    def add_user(self, key: ConversationKey, content: str) -> None:
        self.add(key, "user", content)

    def add_assistant(self, key: ConversationKey, content: str) -> None:
        self.add(key, "assistant", content)

    def snapshot(self, key: ConversationKey) -> list[dict[str, str]]:
        return [item.as_openai_message() for item in self._items.get(key, [])]

    def transcript(self, key: ConversationKey, max_chars: int = 3000) -> str:
        chunks = []
        total = 0
        for item in self._items.get(key, []):
            line = f"{item.role}: {item.content}"
            total += len(line)
            if total > max_chars:
                break
            chunks.append(line)
        return "\n".join(chunks)

    def clear(self, key: ConversationKey) -> None:
        self._items.pop(key, None)

    def extend(self, key: ConversationKey, messages: Iterable[MemoryMessage]) -> None:
        for message in messages:
            self.add(key, message.role, message.content)
