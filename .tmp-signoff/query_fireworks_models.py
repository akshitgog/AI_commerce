#!/usr/bin/env python3
"""Query Fireworks API for available models."""
import os
import sys
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

try:
    from ai_commerce_gateway.core.config import get_settings
    import httpx

    settings = get_settings()
    api_key = settings.llm_api_key.get_secret_value() if settings.llm_api_key else None

    if not api_key:
        print("ERROR: FIREWORKS_API_KEY not configured", file=sys.stderr)
        sys.exit(1)

    # Query Fireworks models endpoint
    response = httpx.get(
        "https://api.fireworks.ai/inference/v1/models",
        headers={"Authorization": f"Bearer {api_key}"},
        timeout=30.0
    )

    if response.status_code != 200:
        print(f"ERROR: Fireworks API returned {response.status_code}", file=sys.stderr)
        print(f"Response: {response.text}", file=sys.stderr)
        sys.exit(1)

    data = response.json()
    models = data.get("data", [])

    # Filter for chat/completion models
    chat_models = []
    for model in models:
        model_id = model.get("id", "")
        # Look for instruction/chat models
        if any(keyword in model_id.lower() for keyword in ["qwen", "llama", "mixtral", "gemma"]):
            chat_models.append({
                "id": model_id,
                "object": model.get("object", ""),
            })

    print("Available chat models:")
    print(json.dumps(chat_models, indent=2))

    # Suggest the first available model
    if chat_models:
        suggested = chat_models[0]["id"]
        print(f"\n✓ Suggested model: fireworks_ai/{suggested}")
    else:
        print("\n⚠ No chat models found in account")

except Exception as e:
    print(f"ERROR: {e}", file=sys.stderr)
    import traceback
    traceback.print_exc()
    sys.exit(1)
