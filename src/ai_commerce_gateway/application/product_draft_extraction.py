"""Merchant AI-assisted catalog creation (D-010): product draft extraction.

Converts free-text merchant input ("I sell a 65W GaN charger, price is
₹1,699, 25 units...") into a structured **draft proposal**.

Trust boundary (D-010): the extractor only *proposes*.  Its output is never
persisted here and never becomes authoritative — the merchant reviews the
draft and publication flows through the frozen ``MerchantCatalogService``
(``create_product`` → DRAFT → review → ``publish_product``).
"""

from __future__ import annotations

import json
import logging
import re
from typing import Final, Literal, Protocol

from litellm import completion
from pydantic import BaseModel, Field

from ai_commerce_gateway.core.errors import AppError, ErrorCode

logger = logging.getLogger(__name__)

_MAX_TEXT_CHARS: Final[int] = 4000
_LLM_TIMEOUT_SECONDS: Final[float] = 30.0

_CORE_DRAFT_FIELDS: Final[tuple[str, ...]] = (
    "title",
    "description",
    "category",
    "price_amount_minor",
    "currency",
    "available_quantity",
)


class ProductDraft(BaseModel):
    """A *proposed* product draft — never authoritative until merchant review."""

    model_config = {"extra": "forbid"}

    title: str | None = None
    description: str | None = None
    category: str | None = None
    price_amount_minor: int | None = Field(default=None, ge=0)
    currency: str | None = Field(default=None, pattern=r"^[A-Z]{3}$")
    available_quantity: int | None = Field(default=None, ge=0)
    attributes: dict[str, str] = Field(default_factory=dict)
    source: Literal["stub", "llm"]
    missing_fields: list[str] = Field(default_factory=list)

    def with_missing_fields(self) -> ProductDraft:
        """Return a copy with ``missing_fields`` computed from core fields."""
        missing = [
            name for name in _CORE_DRAFT_FIELDS if getattr(self, name) is None
        ]
        return self.model_copy(update={"missing_fields": missing})


class ProductDraftExtractor(Protocol):
    """Extracts a structured product draft from merchant natural language."""

    def extract(self, text: str) -> ProductDraft:
        """Return a draft proposal for the merchant's description."""
        ...


def _validate_text(text: str) -> str:
    cleaned = text.strip()
    if not cleaned:
        raise AppError(
            ErrorCode.VALIDATION_ERROR,
            "Merchant product description must not be empty.",
            status_code=400,
        )
    if len(cleaned) > _MAX_TEXT_CHARS:
        raise AppError(
            ErrorCode.VALIDATION_ERROR,
            f"Merchant product description exceeds {_MAX_TEXT_CHARS} characters.",
            status_code=400,
        )
    return cleaned


class StubProductDraftExtractor:
    """Deterministic, offline extractor for demos and tests.

    Uses simple heuristics (no network, no model): first ₹/Rs amount becomes
    the price, the first ``N units``-style phrase becomes stock, the first
    sentence becomes the title.  Mirrors the buyer lane's ``StubLLMClient``
    so the flow works end-to-end without an API key.
    """

    _PRICE_RE = re.compile(r"(?:₹|rs\.?|inr)\s*([0-9][0-9,]*(?:\.[0-9]+)?)", re.IGNORECASE)
    _QUANTITY_RE = re.compile(
        r"(?:stock of\s*)?([0-9][0-9,]*)\s*(?:units?|pieces?|pcs?|items?)\b"
        r"|(?:stock of|quantity of)\s*([0-9][0-9,]*)",
        re.IGNORECASE,
    )
    _PORT_RE = re.compile(r"([0-9]+)\s*[x×]\s*(usb[- ]?[cda](?:\s*port)?)", re.IGNORECASE)

    def extract(self, text: str) -> ProductDraft:
        cleaned = _validate_text(text)

        draft = ProductDraft(source="stub")

        first_line = cleaned.splitlines()[0].strip()
        first_sentence = re.split(r"(?<=\w[.!?])\s", first_line, maxsplit=1)[0]
        title = (first_sentence or first_line).rstrip(".!? ").strip()
        if title:
            draft = draft.model_copy(
                update={"title": title[:80], "description": cleaned}
            )

        price_match = self._PRICE_RE.search(cleaned)
        if price_match:
            rupees = float(price_match.group(1).replace(",", ""))
            draft = draft.model_copy(
                update={
                    "price_amount_minor": int(round(rupees * 100)),
                    "currency": "INR",
                }
            )

        quantity_match = self._QUANTITY_RE.search(cleaned)
        if quantity_match:
            raw = quantity_match.group(1) or quantity_match.group(2)
            if raw:
                draft = draft.model_copy(
                    update={"available_quantity": int(raw.replace(",", ""))}
                )

        ports = [f"{count}× {port.upper()}" for count, port in self._PORT_RE.findall(cleaned)]
        if ports:
            draft = draft.model_copy(update={"attributes": {"ports": ", ".join(ports)}})

        return draft.with_missing_fields()


class LLMProductDraftExtractor:
    """LLM-backed extractor via LiteLLM (OpenAI-compatible and others).

    Active only when ``llm_api_key`` is configured; otherwise the stub is
    used (see ``get_product_draft_extractor`` in the merchant API layer).
    ``provider_url`` maps to LiteLLM's ``api_base`` (None = provider default).
    """

    _SYSTEM_PROMPT: Final[str] = (
        "You extract structured product catalog drafts from a merchant's "
        "natural-language description. Respond with JSON only, no prose, using "
        "exactly this schema: {\"title\": str|null, \"description\": str|null, "
        "\"category\": str|null, \"price_amount_minor\": int|null, "
        "\"currency\": str|null, \"available_quantity\": int|null, "
        "\"attributes\": object}. price_amount_minor is the integer amount in "
        "minor units (paise) of the merchant's stated price. Use null for any "
        "field the merchant did not state. Never invent facts."
    )

    def __init__(self, *, provider_url: str | None, api_key: str, model: str) -> None:
        self._api_base = provider_url.rstrip("/") if provider_url else None
        self._api_key = api_key
        self._model = model

    def extract(self, text: str) -> ProductDraft:
        cleaned = _validate_text(text)
        try:
            response = completion(
                model=self._model,
                api_key=self._api_key,
                api_base=self._api_base,
                messages=[
                    {"role": "system", "content": self._SYSTEM_PROMPT},
                    {"role": "user", "content": cleaned},
                ],
                response_format={"type": "json_object"},
                temperature=0,
                timeout=_LLM_TIMEOUT_SECONDS,
            )
            content = response.choices[0].message.content
            parsed = json.loads(content) if isinstance(content, str) else content
        except AppError:
            raise
        except Exception as exc:
            logger.warning("LLM product draft extraction failed: %s", exc)
            raise AppError(
                ErrorCode.INTERNAL_ERROR,
                "AI extraction is unavailable right now. Use the manual form.",
                status_code=502,
            ) from exc

        if not isinstance(parsed, dict):
            raise AppError(
                ErrorCode.VALIDATION_ERROR,
                "AI extraction returned an unexpected shape.",
                status_code=400,
            )

        return self._to_draft(parsed)

    def _to_draft(self, parsed: dict[str, object]) -> ProductDraft:
        attributes = parsed.get("attributes")
        try:
            draft = ProductDraft(
                title=_optional_str(parsed.get("title")),
                description=_optional_str(parsed.get("description")),
                category=_optional_str(parsed.get("category")),
                price_amount_minor=_optional_int(parsed.get("price_amount_minor")),
                currency=_optional_str(parsed.get("currency")),
                available_quantity=_optional_int(parsed.get("available_quantity")),
                attributes=attributes if isinstance(attributes, dict) else {},
                source="llm",
            )
        except Exception as exc:
            raise AppError(
                ErrorCode.VALIDATION_ERROR,
                "AI extraction returned invalid field values.",
                status_code=400,
            ) from exc
        return draft.with_missing_fields()


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _optional_int(value: object) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    try:
        return int(str(value).strip())
    except ValueError:
        return None
