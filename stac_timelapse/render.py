"""Register STAC item searches and fetch rendered Raster API PNG frames.

STAC items can use either ``datetime`` or interval fields such as
``start_datetime``. Search registration therefore pins requests by item id
instead of relying on datetime matching. Callers that render many frames may
pass a per-run cache to avoid duplicate registrations without leaking state
across process-level pipeline invocations.
"""

from __future__ import annotations

import logging
import time
from typing import Any
from urllib.parse import quote, urljoin

import requests

from .config import Config

LOGGER = logging.getLogger(__name__)


def register_search(
    item: dict[str, Any],
    cfg: Config,
    search_cache: dict[str, str] | None = None,
) -> str:
    """
    Register a Raster API search pinned to a single STAC item and return its search id.

    Filters by item ``id`` so the search works for both point-datetime items and
    interval items (``start_datetime`` / ``end_datetime`` with ``datetime=null``).
    """

    item_id = item["id"]
    if search_cache is not None and item_id in search_cache:
        return search_cache[item_id]

    url = urljoin(_ensure_slash(cfg.raster_api), "searches/register")
    payload = {
        "collections": [cfg.collection_id],
        "filter-lang": "cql2-json",
        "filter": {
            "op": "=",
            "args": [{"property": "id"}, item_id],
        },
        "sortby": [{"field": "datetime", "direction": "asc"}],
    }

    response = _request_with_retries(
        "POST",
        url,
        cfg,
        json=payload,
        timeout=60,
    )
    data = response.json()
    search_id = (
        data.get("searchid")
        or data.get("search_id")
        or data.get("id")
        or data.get("hash")
    )
    if not search_id:
        raise RuntimeError(f"Raster search registration did not return a search id: {data}")

    if search_cache is not None:
        search_cache[item_id] = str(search_id)
    return str(search_id)


def fetch_frame(search_id: str, cfg: Config) -> bytes:
    """
    Fetch a rendered PNG for a registered Raster API search.
    """

    bbox = ",".join(_format_number(value) for value in cfg.bbox)
    path = f"searches/{quote(search_id, safe='')}/bbox/{bbox}/{cfg.width}x{cfg.height}.png"
    url = urljoin(_ensure_slash(cfg.raster_api), path)
    params: list[tuple[str, str]] = []

    for asset in cfg.assets:
        params.append(("assets", asset))
    if cfg.expression:
        params.append(("expression", cfg.expression))
    if cfg.colormap_name:
        params.append(("colormap_name", cfg.colormap_name))
    if cfg.rescale:
        params.append(("rescale", cfg.rescale))
    elif not cfg.algorithm:
        params.append(("algorithm", "percentile_stretch"))
    if cfg.algorithm:
        params.append(("algorithm", cfg.algorithm))
    if cfg.resampling:
        params.append(("resampling", cfg.resampling))
    if cfg.color_formula:
        params.append(("color_formula", cfg.color_formula))

    response = _request_with_retries(
        "GET",
        url,
        cfg,
        params=params,
        timeout=120,
    )
    return response.content


def _request_with_retries(
    method: str,
    url: str,
    cfg: Config,
    retries: int = 3,
    backoff: float = 1.0,
    **kwargs: Any,
) -> requests.Response:
    headers = kwargs.pop("headers", {})
    merged_headers = {**cfg.auth_headers(), **headers}
    last_exc: Exception | None = None

    for attempt in range(1, retries + 1):
        try:
            response = requests.request(method, url, headers=merged_headers, **kwargs)
            if response.status_code < 500:
                response.raise_for_status()
                return response
            LOGGER.warning(
                "Raster API %s %s returned %s on attempt %s/%s",
                method,
                url,
                response.status_code,
                attempt,
                retries,
            )
            last_exc = requests.HTTPError(
                f"{response.status_code} server error for {url}",
                response=response,
            )
        except requests.RequestException as exc:
            last_exc = exc
            if attempt == retries:
                break
            LOGGER.warning(
                "Raster API %s %s failed on attempt %s/%s: %s",
                method,
                url,
                attempt,
                retries,
                exc,
            )
        if attempt < retries:
            time.sleep(backoff * 2 ** (attempt - 1))

    if last_exc is not None:
        raise last_exc
    raise RuntimeError(f"Raster API request failed: {method} {url}")


def _item_datetime(item: dict[str, Any]) -> str:
    props = item.get("properties", {})
    datetime_str = props.get("datetime") or props.get("start_datetime")
    if not datetime_str:
        raise ValueError(
            f"STAC item {item.get('id')!r} has neither 'datetime' nor 'start_datetime'"
        )
    return str(datetime_str)


def _format_number(value: float) -> str:
    return f"{value:g}"


def _ensure_slash(url: str) -> str:
    return url if url.endswith("/") else f"{url}/"
