"""OpenAI Provider Adapter for GPT-4o, GPT-4o-mini."""

from __future__ import annotations

import re
import time
from collections.abc import AsyncIterator

import httpx

from app.modules.modelops.providers.base import BaseLLMAdapter, LLMResponse
from app.modules.modelops.schemas import ChatMessage


class OpenAIAdapter(BaseLLMAdapter):
    """Adapter for OpenAI API."""

    @property
    def provider_type(self) -> str:
        return "openai"

    async def generate(
        self,
        messages: list[ChatMessage],
        temperature: float = 0.2,
        max_tokens: int = 2000,
        **kwargs,
    ) -> LLMResponse:
        start_time = time.perf_counter()
        base_url = self.base_url or "https://api.openai.com/v1"
        endpoint = f"{base_url.rstrip('/')}/chat/completions"

        # Safe offline mock mode when API key is not configured or dummy
        if (
            not self.api_key
            or self.api_key in ("mock", "test", "demo", "placeholder")
            or self.api_key.startswith(("mock", "test", "sk-proj-mock", "dummy"))
        ):
            user_msg = messages[-1].content if messages else ""
            query_line = ""
            if "Câu hỏi của người dùng:" in user_msg:
                query_line = user_msg.split("Câu hỏi của người dùng:")[1].split("\n")[0].strip()
            elif user_msg:
                query_line = user_msg.split("\n")[0].strip()
            query_words = set(re.findall(r"\b\w{2,}\b", query_line.lower()))

            if "TÀI LIỆU TRÍCH XUẤT TỪ KHO TRI THỨC:" in user_msg:
                parts = user_msg.split("TÀI LIỆU TRÍCH XUẤT TỪ KHO TRI THỨC:")
                context_part = parts[1].strip()
                if "--- Đoạn trích" in context_part:
                    chunks = [c.split("---", 1)[-1].strip() for c in context_part.split("--- Đoạn trích") if c.strip()]
                else:
                    chunks = [context_part[:1200]]

                stopwords = {
                    "văn", "bản", "hành", "chính", "quy", "định", "các", "những", "của",
                    "cho", "trong", "theo", "về", "được", "có", "không", "là", "gì",
                    "như", "thế", "nào", "bao", "nhiêu", "trường", "đại", "học", "nhơn"
                }
                target_words = query_words - stopwords or query_words

                # Select best matching chunk based on informative words
                best_chunk = chunks[0] if chunks else context_part[:500]
                best_overlap = -1
                for chk in chunks:
                    chk_words = set(re.findall(r"\b\w{2,}\b", chk.lower()))
                    overlap = len(target_words.intersection(chk_words))
                    if overlap > best_overlap:
                        best_overlap = overlap
                        best_chunk = chk

                # Preserve full chunk if within reasonable length, else extract focused window
                if len(best_chunk) <= 2500:
                    selected_text = best_chunk
                else:
                    lines = [line.strip() for line in best_chunk.split("\n") if line.strip()]
                    relevant_lines = [
                        ln for ln in lines
                        if len(target_words.intersection(set(re.findall(r"\b\w{2,}\b", ln.lower())))) >= 1
                    ]
                    if not relevant_lines:
                        relevant_lines = lines[:15]
                    selected_text = "\n".join(relevant_lines[:20])

                mock_text = (
                    f"Căn cứ quy định chính thức của Trường Đại học Quy Nhơn, xin giải đáp như sau:\n\n"
                    f"{selected_text}"
                )
            elif "BẢNG SỐ LIỆU ĐÃ XÁC THỰC:" in user_msg:
                facts_part = user_msg.split("BẢNG SỐ LIỆU ĐÃ XÁC THỰC:")[1].split("\n\n")[0].strip()
                mock_text = (
                    f"Căn cứ dữ liệu số liệu chính thức của Trường Đại học Quy Nhơn:\n\n"
                    f"{facts_part}"
                )
            else:
                query_text = query_line or user_msg[:100]
                mock_text = (
                    f"Dựa trên tài liệu chính thức của Trường Đại học Quy Nhơn:\n"
                    f"Về câu hỏi '{query_text}', vui lòng tham khảo các quy định hiện hành hoặc liên hệ Hotline 0256.3846.156."
                )
            elapsed = (time.perf_counter() - start_time) * 1000
            prompt_toks = sum(len(m.content.split()) for m in messages) * 2
            comp_toks = len(mock_text.split()) * 2
            return LLMResponse(
                content=mock_text,
                provider=self.provider_type,
                model=self.model_name,
                prompt_tokens=prompt_toks,
                completion_tokens=comp_toks,
                total_tokens=prompt_toks + comp_toks,
                latency_ms=round(elapsed, 2),
            )

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model_name,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        async with httpx.AsyncClient(timeout=self.timeout_seconds, trust_env=False) as client:
            resp = await client.post(endpoint, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        choice = data.get("choices", [{}])[0]
        content = choice.get("message", {}).get("content", "")
        usage = data.get("usage", {})
        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)
        total_tokens = usage.get("total_tokens", prompt_tokens + completion_tokens)
        elapsed = (time.perf_counter() - start_time) * 1000

        return LLMResponse(
            content=content,
            provider=self.provider_type,
            model=self.model_name,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            latency_ms=round(elapsed, 2),
        )

    async def stream(
        self,
        messages: list[ChatMessage],
        temperature: float = 0.2,
        max_tokens: int = 2000,
        **kwargs,
    ) -> AsyncIterator[str]:
        response = await self.generate(messages, temperature=temperature, max_tokens=max_tokens)
        words = response.content.split(" ")
        for word in words:
            yield word + " "
