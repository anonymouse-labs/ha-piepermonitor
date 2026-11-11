"""Adapter for the PieperMonitor feed: turns a feed incident into the message shape the sensors use.

The feed is enriched upstream (priority, vehicles, capcode names, regions), so nothing is derived here.
Schema: see tests/fixtures/feed_v1.json.
"""
from __future__ import annotations

from typing import Any

from .regions import REGIONS, SERVICES, police_unit_regions

SCHEMA_VERSION = 1
# Feed service names -> service ids used by the sensors (Lifeliner stands for the MMT).
SERVICE_IDS = {"POLITIE": "1", "BRANDWEER": "2", "AMBULANCE": "3", "KNRM": "4", "MMT": "5", "DARES": "7"}


def _compact(name: str) -> str:
    return name.lower().replace(" ", "").replace("-", "")


_REGION_BY_NAME = {_compact(name): region_id for region_id, name in REGIONS.items()}


def region_id(name: str) -> str:
    return _REGION_BY_NAME.get(_compact(name), "")


def adapt_incident(item: dict[str, Any]) -> dict[str, Any] | None:
    """One feed incident -> sensor message, or None when it lacks an id, time or text."""
    text = str(item.get("message") or "").strip()
    received = item.get("receivedAt")
    if not text or not received or item.get("id") is None:
        return None
    services = [s for s in item.get("services") or [] if isinstance(s, str)]
    service_id = next((SERVICE_IDS[s] for s in services if s in SERVICE_IDS), "")
    region_names = [r for r in item.get("regions") or [] if isinstance(r, str)]
    unit_regions = next((u for r in region_names if (u := police_unit_regions(r))), None)
    ids = unit_regions or [i for r in region_names if (i := region_id(r))]
    capcodes = [str(c) for c in item.get("capcodes") or []]
    info = item.get("capcodeInfo") or {}
    vehicles = [dict(v) for v in item.get("vehicles") or [] if isinstance(v, dict) and v.get("id")]
    return {
        "api_id": str(item["id"]),
        "message_id": f"pm-{item['id']}",
        "message": text,
        "melding": text,
        "tekstmelding": text,
        "pager_text": text,
        "priority": item.get("priority"),
        "urgency": item.get("urgency"),
        "grip": int(item.get("grip") or 0),
        "escalation": item.get("escalation"),
        "feed_incident_id": item.get("incidentId"),
        "vehicles": vehicles,
        "capcode_details": [{"capcode": c, "description": str(info.get(c, ""))} for c in capcodes],
        "street": "",
        "postcode": "",
        "capcode": capcodes[0] if capcodes else "",
        "capcodes": capcodes,
        "regio": ids[0] if ids else "",
        "regio_name": region_names[0] if region_names else "",
        "regions": ids,
        "discipline": SERVICES.get(service_id, services[0].title() if services else ""),
        "dienstid": service_id,
        "latitude": item.get("lat") if item.get("lat") is not None else "",
        "longitude": item.get("lon") if item.get("lon") is not None else "",
        "published": str(received),
        "source": "piepermonitor",
        "city": str(item.get("city") or ""),
    }


def adapt_feed(payload: Any) -> tuple[list[dict[str, Any]], bool | None]:
    """(messages, live) of a feed payload. Raises ValueError on a missing or newer schema."""
    if not isinstance(payload, dict) or not isinstance(payload.get("incidents"), list):
        raise ValueError("PieperMonitor feed has no 'incidents' list")
    version = payload.get("schemaVersion")
    if not isinstance(version, int) or version > SCHEMA_VERSION:
        raise ValueError(f"PieperMonitor feed schema {version!r} is not supported; update the integration")
    messages = [m for item in payload["incidents"] if isinstance(item, dict) and (m := adapt_incident(item))]
    live = payload.get("live")
    return messages, live if isinstance(live, bool) else None
