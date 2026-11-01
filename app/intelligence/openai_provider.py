"""OpenAI API provider for news classification."""

from __future__ import annotations

import json
import logging
from typing import Optional

from app.config import Settings
from app.intelligence.ai_provider import BaseAIProvider, ClassificationResult, SYSTEM_PROMPT

logger = logging.getLogger("newsedge.intelligence.openai")


class OpenAIProvider(BaseAIProvider):
    """Cloud inference using OpenAI API."""

    def __init__(self, settings: Settings):
        self.api_key = settings.openai_api_key
        self.model = settings.openai_model

    def is_available(self) -> bool:
        return bool(self.api_key and len(self.api_key) > 10)

    def classify_news(
        self,
        headline: str,
        content: str,
        company_name: str,
        nse_symbol: str,
        source_urls: list[str],
        additional_context: Optional[str] = None,
    ) -> ClassificationResult:
        if not self.is_available():
            logger.warning("OpenAI API key not configured. Using heuristic fallback.")
            from app.intelligence.ollama_provider import OllamaProvider
            # Borrow fallback logic
            return OllamaProvider.__dict__["_heuristic_fallback"](
                None, headline, company_name, nse_symbol, source_urls
            )

        try:
            from openai import OpenAI

            client = OpenAI(api_key=self.api_key)

            user_prompt = f"""Headline: {headline}
Company: {company_name} (NSE: {nse_symbol})
Content Summary: {content[:2000]}
Context: {additional_context or 'None'}
"""
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.1,
            )

            raw_text = response.choices[0].message.content or "{}"
            data = json.loads(raw_text)

            return ClassificationResult(
                company_name=data.get("company_name", company_name),
                nse_symbol=data.get("nse_symbol", nse_symbol),
                news_category=data.get("news_category", "OTHER"),
                sentiment=data.get("sentiment", "NEUTRAL"),
                impact_score=float(data.get("impact_score", 50.0)),
                confidence=float(data.get("confidence", 50.0)),
                financial_materiality=data.get("financial_materiality", ""),
                expected_direction=data.get("expected_direction", "neutral").lower(),
                time_horizon=data.get("time_horizon", "intraday"),
                news_summary=data.get("news_summary", headline),
                reasoning=data.get("reasoning", ""),
                risks=data.get("risks", []),
                source_urls=source_urls,
            )
        except Exception as exc:
            logger.error("OpenAI classification failed: %s. Falling back to heuristic.", exc)
            from app.intelligence.ollama_provider import OllamaProvider
            return OllamaProvider.__dict__["_heuristic_fallback"](
                None, headline, company_name, nse_symbol, source_urls
            )
