"""The PieperMonitor feed as alert source: token registration, ETag and rejected tokens."""
from datetime import timedelta
import json
from pathlib import Path

from homeassistant.config_entries import ConfigEntryState
from homeassistant.helpers import issue_registry as ir
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMockResponse

from custom_components.p2000_monitor.const import DATA_FEED, DOMAIN, FEED_LOGIN_URL, FEED_REGISTER_URL, FEED_URL

PAYLOAD = json.loads((Path(__file__).parent / "fixtures" / "feed_v1.json").read_text(encoding="utf-8"))


def hub(options=None):
    sensor = {"subentry_type": "sensor", "title": "All", "unique_id": None,
              "data": {"name": "All", "all_services": True}}
    return MockConfigEntry(domain=DOMAIN, version=2, title="PieperMonitor", unique_id=DOMAIN,
                           data={}, options={"source": "piepermonitor", **(options or {})}, subentries_data=[sensor])


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


async def test_free_tier_polls_every_five_minutes(hass, aioclient_mock):
    aioclient_mock.post(FEED_REGISTER_URL, json={"token": "tok", "tier": "free"})
    aioclient_mock.get(FEED_URL, json=PAYLOAD)
    entry = hub()
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    feed = hass.data[DATA_FEED]
    assert feed.tier == "free"
    assert feed.update_interval == timedelta(seconds=300)


async def test_account_gets_live_and_renews_when_expired(hass, aioclient_mock):
    bodies = []

    async def register(method, url, data):
        bodies.append(data)
        expires = dt_util.utcnow().timestamp() + 3600
        return AiohttpClientMockResponse(method, url, json={"token": "live.x.y", "tier": "live", "plan": "plus",
                                                            "expires": expires, "refresh": "r1"})

    aioclient_mock.post(FEED_REGISTER_URL, side_effect=register)
    aioclient_mock.get(FEED_URL, json=PAYLOAD)
    entry = hub({"account_email": "a@b.nl", "account_refresh": "r1", "scan_interval": 30})
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    feed = hass.data[DATA_FEED]
    assert feed.tier == "live" and feed.plan == "plus"
    assert feed.update_interval == timedelta(seconds=30)
    assert bodies[0]["refresh"] == "r1" and len(bodies[0]["install"]) == 32
    feed._feed_expires = dt_util.utcnow().timestamp() - 1
    await feed.async_refresh()
    assert len(bodies) == 2


async def test_rejected_account_falls_back_to_free(hass, aioclient_mock):
    async def register(method, url, data):
        if data.get("refresh"):
            return AiohttpClientMockResponse(method, url, status=401, json={"error": "account"})
        return AiohttpClientMockResponse(method, url, json={"token": "tok", "tier": "free"})

    aioclient_mock.post(FEED_REGISTER_URL, side_effect=register)
    aioclient_mock.get(FEED_URL, json=PAYLOAD)
    entry = hub({"account_email": "a@b.nl", "account_refresh": "old"})
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED
    feed = hass.data[DATA_FEED]
    assert feed.tier == "free" and feed.update_interval == timedelta(seconds=300)
    assert ir.async_get(hass).async_get_issue(DOMAIN, "account_rejected")


async def test_options_login_stores_refresh_not_password(hass, aioclient_mock):
    aioclient_mock.post(FEED_REGISTER_URL, json={"token": "tok"})
    aioclient_mock.get(FEED_URL, json=PAYLOAD)
    entry = hub()
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    aioclient_mock.post(FEED_LOGIN_URL, status=401, json={"error": "account"})
    result = await hass.config_entries.options.async_init(entry.entry_id)
    form = {"source": "piepermonitor", "brandbase": True, "scan_interval": 30}
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {**form, "account_email": "a@b.nl", "account_password": "wrong"}
    )
    assert result["errors"] == {"base": "invalid_auth"}
    aioclient_mock.clear_requests()
    aioclient_mock.post(FEED_LOGIN_URL, json={"token": "live.x.y", "tier": "live", "refresh": "r1", "expires": 1})
    aioclient_mock.post(FEED_REGISTER_URL, json={"token": "tok"})
    aioclient_mock.get(FEED_URL, json=PAYLOAD)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {**form, "account_email": "a@b.nl", "account_password": "pw"}
    )
    assert result["type"] == "create_entry"
    assert entry.options["account_refresh"] == "r1" and entry.options["account_email"] == "a@b.nl"
    assert "account_password" not in entry.options
    login = calls(aioclient_mock, "POST", FEED_LOGIN_URL)[0][2]
    assert login["email"] == "a@b.nl" and login["password"] == "pw"


async def test_rejected_token_registers_again_then_fails(hass, aioclient_mock):
    aioclient_mock.post(FEED_REGISTER_URL, json={"token": "tok"})
    aioclient_mock.get(FEED_URL, status=401)
    entry = hub()
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.SETUP_RETRY
    assert len(calls(aioclient_mock, "POST", FEED_REGISTER_URL)) == 2  # once, then once more after the 401
