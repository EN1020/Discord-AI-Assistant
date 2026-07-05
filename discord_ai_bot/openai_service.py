from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from openai import OpenAI, OpenAIError

from .config import Settings
from .openai_utils import Source, collect_sources, extract_output_text


class OpenAIServiceError(RuntimeError):
    pass


@dataclass(frozen=True)
class AnswerResult:
    text: str
    sources: list[Source]
    used_web_search: bool


class OpenAIResponder:
    def __init__(self, settings: Settings, client: OpenAI | None = None):
        self.settings = settings
        self.client = client or OpenAI(api_key=settings.openai_api_key)

    async def answer(
        self,
        question: str,
        history: list[dict[str, str]] | None = None,
        force_web: bool = False,
    ) -> AnswerResult:
        use_web = self._use_web_tools(force_web)
        model = self.settings.web_model if use_web else self.settings.chat_model
        messages = list(history or [])
        messages.append({"role": "user", "content": question})

        try:
            response = await asyncio.to_thread(self._create_response, model, messages, use_web)
        except OpenAIError as exc:
            if use_web and not force_web and self.settings.web_search_mode == "auto":
                response = await self._fallback_without_web(messages)
                text = extract_output_text(response) or "(No text returned)"
                return AnswerResult(text=text, sources=[], used_web_search=False)
            raise OpenAIServiceError(f"OpenAI API error: {exc.__class__.__name__}") from exc

        text = extract_output_text(response) or "(No text returned)"
        sources = collect_sources(response)
        return AnswerResult(text=text, sources=sources, used_web_search=use_web)

    def _create_response(self, model: str, messages: list[dict[str, str]], use_web: bool) -> Any:
        kwargs: dict[str, Any] = {
            "model": model,
            "instructions": self._instructions(use_web=use_web),
            "input": messages,
        }
        if use_web:
            kwargs.update(
                {
                    "tools": [self._web_search_tool()],
                    "tool_choice": "auto",
                    "include": ["web_search_call.action.sources"],
                }
            )
        return self.client.responses.create(**kwargs)

    async def _fallback_without_web(self, messages: list[dict[str, str]]) -> Any:
        try:
            return await asyncio.to_thread(
                self._create_response,
                self.settings.chat_model,
                messages,
                False,
            )
        except OpenAIError as exc:
            raise OpenAIServiceError(f"OpenAI API error: {exc.__class__.__name__}") from exc

    def _use_web_tools(self, force_web: bool) -> bool:
        if force_web:
            return True
        if self.settings.web_search_mode == "off":
            return False
        return self.settings.web_search_mode in {"auto", "always"}

    def _instructions(self, use_web: bool) -> str:
        current_date = self._current_date_text()
        search_policy = (
            "Use web search for current, recent, time-sensitive, factual, legal, financial, "
            "software-version, product, schedule, price, or news questions. Cite sources when "
            "web information is used. If sources are weak or unavailable, say what is uncertain."
            if use_web
            else "Answer from the conversation and your general knowledge. Say when you are unsure."
        )
        return "\n".join(
            [
                self.settings.system_prompt,
                f"Current date: {current_date}.",
                "Reply in Traditional Chinese by default unless the user asks for another language.",
                search_policy,
            ]
        )

    def _current_date_text(self) -> str:
        timezone_name = self.settings.user_location_timezone or "UTC"
        try:
            tz = ZoneInfo(timezone_name)
        except ZoneInfoNotFoundError:
            tz = ZoneInfo("UTC")
        return datetime.now(tz).strftime("%Y-%m-%d")

    def _web_search_tool(self) -> dict[str, Any]:
        tool: dict[str, Any] = {
            "type": "web_search",
            "external_web_access": self.settings.web_search_live,
        }
        filters: dict[str, Any] = {}
        if self.settings.web_search_allowed_domains:
            filters["allowed_domains"] = list(self.settings.web_search_allowed_domains)
        if self.settings.web_search_blocked_domains:
            filters["blocked_domains"] = list(self.settings.web_search_blocked_domains)
        if filters:
            tool["filters"] = filters

        location = self._user_location()
        if location:
            tool["user_location"] = location
        return tool

    def _user_location(self) -> dict[str, str] | None:
        fields = {
            "country": self.settings.user_location_country,
            "city": self.settings.user_location_city,
            "region": self.settings.user_location_region,
            "timezone": self.settings.user_location_timezone,
        }
        location = {key: value for key, value in fields.items() if value}
        if not location:
            return None
        return {"type": "approximate", **location}
