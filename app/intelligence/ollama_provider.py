"""Ollama local LLM provider for news classification."""

from __future__ import annotations

import json
import logging
import re
import threading
from typing import Optional

import requests

from app.config import Settings
from app.intelligence.ai_provider import BaseAIProvider, ClassificationResult, SYSTEM_PROMPT

logger = logging.getLogger("newsedge.intelligence.ollama")

# Global lock to serialize inference calls to local Ollama daemon
# Prevents multiple concurrent threads from causing socket read timeouts
_OLLAMA_INFERENCE_LOCK = threading.Lock()


def _safe_float(val, default: float = 50.0) -> float:
    """Safely convert strings, None, or percentages to float without ValueError."""
    if val is None:
        return default
    if isinstance(val, (int, float)):
        return float(val)
    if isinstance(val, str):
        # Extract first numeric sequence like '85' from '85%' or '85.5'
        match = re.search(r"[-+]?\d*\.?\d+", val)
        if match:
            try:
                return float(match.group(0))
            except Exception:
                pass
    return default


def _extract_fields_via_regex(text: str) -> dict:
    """Fallback extractor if Ollama's returned JSON was truncated or had syntax issues."""
    data = {}
    patterns = {
        "company_name": r'"company_name"\s*:\s*"([^"]+)"',
        "nse_symbol": r'"nse_symbol"\s*:\s*"([^"]+)"',
        "news_category": r'"news_category"\s*:\s*"([^"]+)"',
        "sentiment": r'"sentiment"\s*:\s*"([^"]+)"',
        "impact_score": r'"impact_score"\s*:\s*([0-9.]+)',
        "confidence": r'"confidence"\s*:\s*([0-9.]+)',
        "expected_direction": r'"expected_direction"\s*:\s*"([^"]+)"',
        "financial_materiality": r'"financial_materiality"\s*:\s*"([^"]+)"',
        "news_summary": r'"news_summary"\s*:\s*"([^"]+)"',
        "reasoning": r'"reasoning"\s*:\s*"([^"]+)"',
    }
    for key, pat in patterns.items():
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            data[key] = m.group(1).strip()
    return data


class OllamaProvider(BaseAIProvider):
    """Local inference using Ollama API."""

    def __init__(self, settings: Settings):
        self.base_url = settings.ollama_base_url.rstrip("/")
        self.model = settings.ollama_model

    def is_available(self) -> bool:
        try:
            resp = requests.get(f"{self.base_url}/api/tags", timeout=3)
            if resp.status_code != 200:
                return False
            data = resp.json()
            models = [m.get("name", "") for m in data.get("models", [])]
            return any(self.model in m for m in models)
        except Exception:
            return False

    def classify_news(
        self,
        headline: str,
        content: str,
        company_name: str,
        nse_symbol: str,
        source_urls: list[str],
        additional_context: Optional[str] = None,
    ) -> ClassificationResult:
        from app.processors.company_knowledge import get_company_profile

        is_known = bool(nse_symbol and nse_symbol not in ("UNKNOWN", "N/A", ""))
        prof = get_company_profile(nse_symbol) if is_known else None
        prof_info = ""
        if prof:
            prof_info = f"\nCompany Business: {prof.business_summary}\nKey Catalysts: Positives: {', '.join(prof.positive_catalysts[:2])} | Risks: {', '.join(prof.negative_catalysts[:2])}"

        if is_known:
            comp_instruction = f"Verified Listed Stock: {company_name} (NSE: {nse_symbol}). Do NOT alter the nse_symbol or company_name.{prof_info}"
        else:
            comp_instruction = "Company unverified. Identify the primary listed Indian stock from the headline/summary and its official NSE ticker."

        user_prompt = f"""Headline: {headline}
{comp_instruction}
Summary: {content[:350]}
"""
        payload = {
            "model": self.model,
            "prompt": f"{SYSTEM_PROMPT}\n\nAnalyze this news event:\n{user_prompt}",
            "stream": False,
            "format": "json",
            "options": {
                "temperature": 0.1,
                "num_predict": 450,  # Generous token budget to avoid truncated JSON
            },
        }

        try:
            # Serialize inference through the global lock to prevent queue timeouts
            with _OLLAMA_INFERENCE_LOCK:
                resp = requests.post(f"{self.base_url}/api/generate", json=payload, timeout=90)
                resp.raise_for_status()
                raw_response = resp.json().get("response", "{}")

            # Extract JSON
            match = re.search(r"\{.*\}", raw_response, re.DOTALL)
            if match:
                json_str = match.group(0)
            else:
                json_str = raw_response.strip()
                if "{" in json_str:
                    json_str = json_str[json_str.find("{"):]
                    if json_str.count('"') % 2 != 0:
                        json_str += '"'
                    if not json_str.endswith("}"):
                        json_str += "}"

            data = {}
            try:
                data = json.loads(json_str)
            except Exception as j_err:
                logger.debug("Ollama JSON parse warning (%s). Applying regex field rescue.", j_err)
                data = _extract_fields_via_regex(raw_response)

            from app.processors.nse_master import get_nse_resolver
            resolver = get_nse_resolver()

            # Validate returned symbols: reject known hallucinations
            returned_sym = (data.get("nse_symbol") or nse_symbol).upper().strip()
            returned_name = data.get("company_name", company_name)

            if returned_sym in ("LARSUN", "LARSEN"):
                returned_sym = "LT"
            elif returned_sym in ("DURABAR", "GAILINDIA"):
                returned_sym = "GAIL"

            # If returned symbol is not valid, rescue via symbol guess or fallback
            if not resolver.is_valid_nse_symbol(returned_sym):
                guess = resolver.resolve_from_symbol_guess(returned_sym)
                if guess:
                    returned_sym = guess["symbol"]
                    returned_name = guess["name"]
                elif is_known and resolver.is_valid_nse_symbol(nse_symbol):
                    returned_sym = nse_symbol
                    returned_name = company_name

            return ClassificationResult(
                company_name=returned_name,
                nse_symbol=returned_sym,
                news_category=data.get("news_category", "OTHER"),
                sentiment=data.get("sentiment", "NEUTRAL"),
                impact_score=_safe_float(data.get("impact_score"), 50.0),
                confidence=_safe_float(data.get("confidence"), 60.0),
                financial_materiality=str(data.get("financial_materiality", "")),
                expected_direction=str(data.get("expected_direction", "neutral")).lower(),
                time_horizon=str(data.get("time_horizon", "intraday")),
                news_summary=str(data.get("news_summary", headline)),
                reasoning=str(data.get("reasoning", "")),
                risks=data.get("risks", []) if isinstance(data.get("risks"), list) else [],
                source_urls=source_urls,
            )
        except Exception as exc:
            logger.warning("Ollama call failed (%s). Using high-precision catalyst heuristic.", exc)
            return self._heuristic_fallback(headline, company_name, nse_symbol, source_urls)
