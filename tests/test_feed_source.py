"""The PieperMonitor feed as alert source: token registration, ETag and rejected tokens."""
import json
from pathlib import Path

from homeassistant.config_entries import ConfigEntryState
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.p2000_monitor.const import DATA_FEED, DOMAIN, FEED_REGISTER_URL, FEED_URL

PAYLOAD = json.loads((Path(__file__).parent / "fixtures" / "feed_v1.json").read_text(encoding="utf-8"))


def hub():
    sensor = {"subentry_type": "sensor", "title": "All", "unique_id": None,
              "data": {"name": "All", "all_services": True}}
    return MockConfigEntry(domain=DOMAIN, version=2, title="PieperMonitor", unique_id=DOMAIN,
                           data={}, options={"source": "piepermonitor"}, subentries_data=[sensor])


def calls(aioclient_mock, method, url):
    return [c for c in aioclient_mock.mock_calls if c[0] == method and str(c[1]) == url]


async def test_feed_source_registers_once_and_adapts(hass, aioclient_mock):
    aioclient_mock.post(FEED_REGISTER_URL, json={"token": "tok"})
    aioclient_mock.get(FEED_URL, json=PAYLOAD, headers={"ETag": '"v1"'})
    entry = hub()
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED
    feed = hass.data[DATA_FEED]
    assert [m["message_id"] for m in feed.data["messages"]] == ["pm-305002", "pm-305001"]
    assert {m["source"] for m in feed.data["messages"]} == {"piepermonitor"}
    assert len(calls(aioclient_mock, "POST", FEED_REGISTER_URL)) == 1
    headers = calls(aioclient_mock, "GET", FEED_URL)[0][3]
    assert headers["X-PM-Token"] == "tok" and len(headers["X-PM-Install"]) == 32


async def test_not_modified_reuses_messages(hass, aioclient_mock):
    aioclient_mock.post(FEED_REGISTER_URL, json={"token": "tok"})
    aioclient_mock.get(FEED_URL, json=PAYLOAD, headers={"ETag": '"v1"'})
    entry = hub()
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    feed = hass.data[DATA_FEED]
    aioclient_mock.clear_requests()
    aioclient_mock.get(FEED_URL, status=304)
    await feed.async_refresh()
    assert feed.last_update_success
    assert len(feed.data["messages"]) == 2
    assert calls(aioclient_mock, "GET", FEED_URL)[0][3]["If-None-Match"] == '"v1"'
    assert not calls(aioclient_mock, "POST", FEED_REGISTER_URL)  # the token is kept


async def test_rejected_token_registers_again_then_fails(hass, aioclient_mock):
    aioclient_mock.post(FEED_REGISTER_URL, json={"token": "tok"})
    aioclient_mock.get(FEED_URL, status=401)
    entry = hub()
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.SETUP_RETRY
    assert len(calls(aioclient_mock, "POST", FEED_REGISTER_URL)) == 2  # once, then once more after the 401
