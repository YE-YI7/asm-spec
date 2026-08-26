"""Candidate discovery-time access extension for AI Catalog entries.

This module intentionally uses an ASM-owned namespace while ai-catalog#83 is
still open.  It keeps discovery signals separate from runtime settlement:
price echoes are non-authoritative, while caller-specific prices may be
resolved through an authenticated resource reference.
"""

from __future__ import annotations

from typing import Any

ACCESS_EXTENSION_KEY = "io.github.ye-yi7.asm.access"
ACCESS_EXTENSION_VERSION = "0.1"


def infer_access_tier(manifest: dict[str, Any]) -> str:
    """Mirror the live catalog's current coarse access-tier derivation."""
    pricing = manifest.get("pricing") or {}
    payment = manifest.get("payment") or {}
    dimensions = pricing.get("billing_dimensions") or []
    methods = payment.get("methods") or []
    has_free = "free_tier" in methods
    has_public_price = any((item.get("cost_per_unit") or 0) > 0 for item in dimensions)

    if has_free and has_public_price:
        return "freemium"
    if has_free:
        return "free"
    if has_public_price:
        return "subscription" if "subscription" in methods else "paid"
    return "negotiated"


def _price_echoes(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    pricing = manifest.get("pricing") or {}
    as_of = (manifest.get("provenance") or {}).get("last_verified_at")
    estimated = bool(pricing.get("estimated"))
    echoes: list[dict[str, Any]] = []

    for item in pricing.get("billing_dimensions") or []:
        if (item.get("cost_per_unit") or 0) <= 0:
            continue
        echo = {
            "dimension": item.get("dimension"),
            "unit": item.get("unit"),
            "amount": item.get("cost_per_unit"),
            "currency": item.get("currency", "USD"),
        }
        if as_of:
            echo["asOf"] = as_of
        if estimated:
            echo["estimated"] = True
        echoes.append({key: value for key, value in echo.items() if value is not None})

    return echoes


def _free_tier_rules(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    free_tier = (manifest.get("pricing") or {}).get("free_tier")
    if free_tier is None:
        return []
    if isinstance(free_tier, str):
        return [{"description": free_tier}]
    if isinstance(free_tier, dict):
        return [free_tier]
    if isinstance(free_tier, list):
        return [item for item in free_tier if isinstance(item, dict)]
    return []


def derive_access_extension(manifest: dict[str, Any]) -> dict[str, Any]:
    """Return the candidate nested extension value for one ASM manifest."""
    pricing = manifest.get("pricing") or {}
    payment = manifest.get("payment") or {}
    provenance = manifest.get("provenance") or {}
    methods = payment.get("methods") or []

    extension: dict[str, Any] = {
        "version": ACCESS_EXTENSION_VERSION,
        "tier": infer_access_tier(manifest),
        "mechanisms": list(dict.fromkeys(methods)),
        "priceEchoes": _price_echoes(manifest),
        "freeTierRules": _free_tier_rules(manifest),
        "source": {
            "url": provenance.get("source_url"),
            "retrievedAt": provenance.get("last_verified_at"),
        },
    }

    pricing_url = payment.get("signup_url") or provenance.get("source_url")
    if pricing_url:
        extension["pricingUrl"] = pricing_url

    resolver = pricing.get("resolver")
    if isinstance(resolver, dict) and resolver.get("url"):
        extension["pricingResolver"] = resolver

    return extension
