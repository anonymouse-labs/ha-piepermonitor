"""Shared fixtures for PieperMonitor tests."""
import sys
from unittest.mock import patch

import pytest

if sys.platform == "win32":
    # Windows event loops need a local socketpair; HTTP stays mocked by aioclient_mock.
    import pytest_socket

    pytest_socket.disable_socket = lambda *a, **k: None


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    yield


@pytest.fixture(autouse=True)
def legacy_source_by_default():
    """Entries without a source option use the feed in production; the older tests mock the legacy API."""
    with patch("custom_components.p2000_monitor.DEFAULT_SOURCE", "legacy"), patch(
        "custom_components.p2000_monitor.config_flow.DEFAULT_SOURCE", "legacy"
    ):
        yield
