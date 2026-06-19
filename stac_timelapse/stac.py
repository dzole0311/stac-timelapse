"""Query STAC APIs for renderable items.

Public runs use pystac-client first for standard STAC behavior. Authenticated
runs use requests directly so bearer tokens are carried through paginated
searches. Collections often publish interval items with ``datetime=null``,
so sorting and labels always fall back to ``start_datetime``.
"""

from __future__ import annotations

import logging
from typing import Any
from urllib.parse import urljoin

import requests

from .config import Config

LOGGER = logging.getLogger(__name__)


def get_items(cfg: Config) -> list[dict[str, Any]]:
    """
    Query the STAC API and return items sorted by datetime ascending.

    The unauthenticated path tries ``pystac-client`` first, then falls back to a
    raw requests implementation. Authenticated runs use raw requests so the
    bearer token is passed consistently across pagination links.
    """

    cfg.validate()
    if not cfg.auth_token:
        try:
            return _get_items_with_pystac(cfg)
        except Exception as exc:  # pragma: no cover - live service fallback path
            LOGGER.warning("pystac-client search failed; retrying with requests: %s", exc)

    items = _get_items_with_requests(cfg)
    _log_item_summary(items)
    return items


def _get_items_with_pystac(cfg: Config) -> list[dict[str, Any]]:
    from pystac_client import Client

    client = Client.open(cfg.stac_api)
    search = client.search(
        collections=[cfg.collection_id],
        datetime=cfg.datetime_interval,
        bbox=cfg.bbox,
    )
    items = [item.to_dict() for item in search.items()]
    items = _sort_items(items)
    _log_item_summary(items)
    return items


def _get_items_with_requests(cfg: Config) -> list[dict[str, Any]]:
    session = requests.Session()
    session.headers.update(cfg.auth_headers())
    search_url = urljoin(_ensure_slash(cfg.stac_api), "search")
    payload: dict[str, Any] = {
        "collections": [cfg.collection_id],
        "datetime": cfg.datetime_interval,
        "bbox": cfg.bbox,
        "limit": 100,
    }

    items: list[dict[str, Any]] = []
    next_url: str | None = search_url
    next_payload: dict[str, Any] | None = payload
    next_method = "POST"

    while next_url:
        if next_method == "GET":
            response = session.get(next_url, timeout=60)
        else:
            response = session.post(next_url, json=next_payload, timeout=60)
        response.raise_for_status()
        page = response.json()
        items.extend(page.get("features", []))

        next_url = None
        next_payload = None
        next_method = "POST"
        for link in page.get("links", []):
            if link.get("rel") == "next" and link.get("href"):
                next_url = urljoin(search_url, link["href"])
                next_method = link.get("method", "GET").upper()
                next_payload = link.get("body")
                break

    return _sort_items(items)


def _sort_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    def _sort_key(item: dict[str, Any]) -> str:
        props = item.get("properties", {})
        return props.get("datetime") or props.get("start_datetime") or ""

    return sorted(items, key=_sort_key)


def _log_item_summary(items: list[dict[str, Any]]) -> None:
    if not items:
        LOGGER.info("Found 0 STAC items")
        return
    first = _item_label(items[0])
    last = _item_label(items[-1])
    LOGGER.info("Found %s STAC items from %s to %s", len(items), first, last)


def _item_label(item: dict[str, Any]) -> str:
    props = item.get("properties", {})
    return props.get("datetime") or props.get("start_datetime") or "unknown"


def _ensure_slash(url: str) -> str:
    return url if url.endswith("/") else f"{url}/"
