"""Adapter for the PieperMonitor feed: pure functions, no Home Assistant needed."""
import json
from pathlib import Path

import pytest

from custom_components.p2000_monitor.feed import adapt_feed, adapt_incident

FEED = json.loads((Path(__file__).parent / "fixtures" / "feed_v1.json").read_text(encoding="utf-8"))


def test_adapt_ambulance_a0():
    messages, live = adapt_feed(FEED)
    assert live is True
    ambulance = messages[0]
    assert ambulance["message_id"] == "pm-305001"
    assert ambulance["dienstid"] == "3"
    assert ambulance["discipline"] == "Ambulancediensten"
    assert ambulance["vehicles"] == []
    assert (ambulance["priority"], ambulance["urgency"]) == ("A0", 1)
    assert ambulance["regio"] == "21"
    assert ambulance["regions"] == ["21"]
    assert ambulance["latitude"] == 50.9477
    assert ambulance["source"] == "piepermonitor"
    assert ambulance["capcode_details"] == [{"capcode": "1023193", "description": "Ambulance Westelijke Mijnstreek"}]


def test_adapt_fire_keeps_vehicle_names():
    fire = adapt_feed(FEED)[0][1]
    assert fire["dienstid"] == "2"
    assert fire["vehicles"] == [{"id": "24-3231", "type": "Tankautospuit", "station": "Maastricht"}]
    assert fire["latitude"] == "" and fire["longitude"] == ""
    assert fire["escalation"] == "Middel"
    assert fire["capcodes"] == ["1005258", "1005264"]


@pytest.mark.parametrize("name,expected", [("Noord-Holland Noord", "24"), ("Hollands Midden", "5"), ("Onbekend", "")])
def test_region_names_map_to_ids(name, expected):
    message = adapt_incident({**FEED["incidents"][0], "regions": [name]})
    assert message["regio"] == expected


def test_police_unit_covers_all_its_regions():
    message = adapt_incident({**FEED["incidents"][0], "services": ["POLITIE"], "regions": ["Eenheid Limburg"]})
    assert message["regions"] == ["15", "21"]
    assert message["dienstid"] == "1"


def test_incomplete_incident_is_skipped():
    assert adapt_incident({"id": 1, "message": "", "receivedAt": "2026-11-08T19:12:00+00:00"}) is None
    assert adapt_incident({"message": "P 1 x", "receivedAt": "2026-11-08T19:12:00+00:00"}) is None


@pytest.mark.parametrize("payload", [None, [], {"incidents": "x"}, {"incidents": [], "schemaVersion": 2}, {"incidents": []}])
def test_bad_or_newer_feed_raises(payload):
    with pytest.raises(ValueError):
        adapt_feed(payload)
