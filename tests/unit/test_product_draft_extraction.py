"""D-010 merchant AI-assisted catalog creation — extraction layer tests.

Covers the propose-only trust boundary: the extractor and endpoint produce
drafts and never persist anything; publication flows only through the
frozen catalog services.
"""

import json

import pytest

from ai_commerce_gateway.application import product_draft_extraction as pde
from ai_commerce_gateway.application.product_draft_extraction import (
    LLMProductDraftExtractor,
    StubProductDraftExtractor,
)
from ai_commerce_gateway.core.errors import AppError

# ---------------------------------------------------------------------------
# StubProductDraftExtractor — deterministic heuristics
# ---------------------------------------------------------------------------


class TestStubProductDraftExtractor:
    def test_full_description_draft(self):
        extractor = StubProductDraftExtractor()
        draft = extractor.extract(
            "65W GaN Fast Charger. Compact charger with 2× USB-C and 1× USB-A. "
            "Price is ₹1,699 and I have 25 units."
        )
        assert draft.source == "stub"
        assert draft.title == "65W GaN Fast Charger"
        assert draft.price_amount_minor == 169900  # ₹1,699 → paise
        assert draft.currency == "INR"
        assert draft.available_quantity == 25
        assert "USB-C" in draft.attributes.get("ports", "")
        assert draft.missing_fields == ["category"]

    def test_missing_fields_reported(self):
        extractor = StubProductDraftExtractor()
        draft = extractor.extract("A handcrafted wooden stool")
        assert draft.title is not None
        assert draft.price_amount_minor is None
        assert draft.available_quantity is None
        assert set(draft.missing_fields) == {
            "category",
            "price_amount_minor",
            "currency",
            "available_quantity",
        }

    def test_deterministic(self):
        extractor = StubProductDraftExtractor()
        text = "Wireless mouse, ₹799, 40 units in stock"
        assert extractor.extract(text).model_dump() == extractor.extract(text).model_dump()

    def test_rs_prefix_also_matches(self):
        extractor = StubProductDraftExtractor()
        draft = extractor.extract("Desk mat. Rs 449. 12 units.")
        assert draft.price_amount_minor == 44900
        assert draft.currency == "INR"

    def test_empty_text_rejected(self):
        with pytest.raises(AppError) as exc_info:
            StubProductDraftExtractor().extract("   ")
        assert exc_info.value.status_code == 400

    def test_oversized_text_rejected(self):
        with pytest.raises(AppError) as exc_info:
            StubProductDraftExtractor().extract("x" * 4001)
        assert "4000" in exc_info.value.message


# ---------------------------------------------------------------------------
# LLMProductDraftExtractor — mocked LiteLLM transport
# ---------------------------------------------------------------------------


class _FakeMessage:
    def __init__(self, content: str) -> None:
        self.content = content


class _FakeChoice:
    def __init__(self, content: str) -> None:
        self.message = _FakeMessage(content)


class _FakeResponse:
    def __init__(self, content: str) -> None:
        self.choices = [_FakeChoice(content)]


def _patch_llm(monkeypatch: pytest.MonkeyPatch, body: dict | Exception) -> None:
    def fake_completion(*args: object, **kwargs: object) -> _FakeResponse:
        if isinstance(body, Exception):
            raise body
        return _FakeResponse(json.dumps(body))

    monkeypatch.setattr(pde, "completion", fake_completion)


class TestLLMProductDraftExtractor:
    def _extractor(self) -> LLMProductDraftExtractor:
        return LLMProductDraftExtractor(
            provider_url="https://llm.test/v1",
            api_key="sk_test",
            model="test-model",
        )

    def test_valid_llm_response(self, monkeypatch: pytest.MonkeyPatch):
        _patch_llm(
            monkeypatch,
            {
                "title": "65W GaN Charger",
                "description": "Compact fast charger",
                "category": "Chargers",
                "price_amount_minor": 169900,
                "currency": "INR",
                "available_quantity": 25,
                "attributes": {"ports": "2x USB-C"},
            },
        )
        draft = self._extractor().extract("I sell a 65W GaN charger for 1699 rupees")
        assert draft.source == "llm"
        assert draft.title == "65W GaN Charger"
        assert draft.price_amount_minor == 169900
        assert draft.missing_fields == []

    def test_llm_transport_failure_maps_to_502(self, monkeypatch: pytest.MonkeyPatch):
        _patch_llm(monkeypatch, ConnectionError("boom"))
        with pytest.raises(AppError) as exc_info:
            self._extractor().extract("A nice lamp")
        assert exc_info.value.status_code == 502

    def test_llm_non_dict_payload_rejected(self, monkeypatch: pytest.MonkeyPatch):
        def fake_completion(*args: object, **kwargs: object) -> _FakeResponse:
            return _FakeResponse("[1,2,3]")

        monkeypatch.setattr(pde, "completion", fake_completion)
        with pytest.raises(AppError) as exc_info:
            self._extractor().extract("A nice lamp")
        assert exc_info.value.status_code == 400

    def test_llm_never_invents_missing_fields(self, monkeypatch: pytest.MonkeyPatch):
        _patch_llm(
            monkeypatch,
            {
                "title": "Wooden stool",
                "description": None,
                "category": None,
                "price_amount_minor": None,
                "currency": None,
                "available_quantity": None,
                "attributes": {},
            },
        )
        draft = self._extractor().extract("A wooden stool")
        assert draft.price_amount_minor is None
        assert set(draft.missing_fields) == {
            "description",
            "category",
            "price_amount_minor",
            "currency",
            "available_quantity",
        }
