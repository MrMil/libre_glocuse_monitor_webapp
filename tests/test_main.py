from __future__ import annotations

import asyncio
from datetime import datetime
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from pylibrelinkup.models.data import Trend

import app.main as main_mod
from app.libre import GlucoseReading, GlucoseThresholds, GraphPoint
from app.main import app

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator


@pytest.fixture(autouse=True)
def _skip_startup_poller() -> None:
    """Prevent the real startup handler from running during tests."""
    main_mod._cached_thresholds = None


@pytest.fixture()
async def client() -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


def _make_reading(value: float = 120.0) -> GlucoseReading:
    return GlucoseReading(
        value=value,
        value_in_mg_per_dl=value,
        trend=Trend.STABLE,
        trend_arrow="→",
        timestamp=datetime(2026, 2, 24, 10, 0, 0),
        is_high=False,
        is_low=False,
    )


def _make_thresholds() -> GlucoseThresholds:
    return GlucoseThresholds(urgent_low=55, target_low=70, target_high=180)


class TestIndexPage:
    @pytest.mark.anyio()
    async def test_returns_html(self, client: AsyncClient) -> None:
        resp = await client.get("/")
        assert resp.status_code == 200
        assert "text/html" in resp.headers["content-type"]
        assert "Sugar Monitor" in resp.text


class TestHistoryPage:
    @pytest.mark.anyio()
    async def test_returns_html(self, client: AsyncClient) -> None:
        resp = await client.get("/history")
        assert resp.status_code == 200
        assert "text/html" in resp.headers["content-type"]
        assert "History" in resp.text


class TestApiCurrent:
    @pytest.mark.anyio()
    @patch("app.main.get_current_reading")
    async def test_success(self, mock_get: MagicMock, client: AsyncClient) -> None:
        reading = _make_reading(130.0)
        mock_get.return_value = reading

        resp = await client.get("/api/current")
        assert resp.status_code == 200
        data = resp.json()
        assert data["value"] == 130.0
        assert data["trend_name"] == "STABLE"
        assert "timestamp" in data

    @pytest.mark.anyio()
    @patch("app.main.get_current_reading")
    async def test_error(self, mock_get: MagicMock, client: AsyncClient) -> None:
        mock_get.side_effect = RuntimeError("API down")

        resp = await client.get("/api/current")
        assert resp.status_code == 500
        assert "error" in resp.json()


class TestApiGraph:
    @pytest.mark.anyio()
    @patch("app.main.get_graph_data")
    async def test_success(self, mock_get: MagicMock, client: AsyncClient) -> None:
        reading = _make_reading(150.0)
        points = [
            GraphPoint(value=100.0, timestamp="2026-02-24T08:00:00"),
            GraphPoint(value=110.0, timestamp="2026-02-24T09:00:00"),
        ]
        thresholds = _make_thresholds()
        mock_get.return_value = (reading, points, thresholds)

        resp = await client.get("/api/graph")
        assert resp.status_code == 200
        data = resp.json()
        assert data["current"]["value"] == 150.0
        assert len(data["graph"]) == 2
        assert data["thresholds"]["target_low"] == 70

    @pytest.mark.anyio()
    @patch("app.main.get_graph_data")
    async def test_error(self, mock_get: MagicMock, client: AsyncClient) -> None:
        mock_get.side_effect = RuntimeError("fail")

        resp = await client.get("/api/graph")
        assert resp.status_code == 500
        assert "error" in resp.json()


class TestApiHistory:
    @pytest.mark.anyio()
    @patch("app.main.get_all_readings")
    async def test_success_with_cached_thresholds(
        self, mock_get: MagicMock, client: AsyncClient
    ) -> None:
        main_mod._cached_thresholds = _make_thresholds()
        mock_get.return_value = [
            ("2026-02-24T10:00:00", 120.0),
            ("2026-02-24T09:00:00", 110.0),
        ]

        resp = await client.get("/api/history")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["points"]) == 2
        assert data["thresholds"]["target_low"] == 70

    @pytest.mark.anyio()
    @patch("app.main.get_all_readings")
    async def test_uses_default_thresholds(self, mock_get: MagicMock, client: AsyncClient) -> None:
        main_mod._cached_thresholds = None
        mock_get.return_value = [("2026-02-24T10:00:00", 120.0)]

        resp = await client.get("/api/history")
        data = resp.json()
        assert data["thresholds"]["urgent_low"] == 55
        assert data["thresholds"]["target_low"] == 70
        assert data["thresholds"]["target_high"] == 180

    @pytest.mark.anyio()
    @patch("app.main.get_all_readings")
    async def test_error(self, mock_get: MagicMock, client: AsyncClient) -> None:
        mock_get.side_effect = RuntimeError("db error")

        resp = await client.get("/api/history")
        assert resp.status_code == 500
        assert "error" in resp.json()


class TestLifespanAndPoller:
    @pytest.mark.anyio()
    @patch("app.main._background_poller")
    @patch("app.main.asyncio.to_thread")
    @patch("app.main.init_db")
    async def test_lifespan_calls_init_and_poll(
        self,
        mock_init: MagicMock,
        mock_to_thread: MagicMock,
        mock_poller: MagicMock,
    ) -> None:
        async with main_mod.lifespan(app):
            mock_init.assert_called_once()
            mock_to_thread.assert_called_once_with(main_mod._poll_and_store)

    @pytest.mark.anyio()
    @patch("app.main._poll_and_store")
    async def test_background_poller_runs_once(self, mock_poll: MagicMock) -> None:
        """Test that the poller calls _poll_and_store then sleeps."""
        call_count = 0

        async def fake_sleep(secs: float) -> None:
            nonlocal call_count
            call_count += 1
            if call_count >= 1:
                raise asyncio.CancelledError()

        with (
            patch("app.main.asyncio.sleep", side_effect=fake_sleep),
            pytest.raises(asyncio.CancelledError),
        ):
            await main_mod._background_poller()
        mock_poll.assert_called_once()


class TestPollAndStore:
    @patch("app.main.upsert_readings")
    @patch("app.main.collect_readings")
    def test_stores_readings(self, mock_collect: MagicMock, mock_upsert: MagicMock) -> None:
        thresholds = _make_thresholds()
        rows = [("2026-02-24T10:00:00", 120.0)]
        mock_collect.return_value = (rows, thresholds)
        mock_upsert.return_value = 1

        main_mod._poll_and_store()

        mock_upsert.assert_called_once_with(rows)
        assert main_mod._cached_thresholds is thresholds

    @patch("app.main.collect_readings")
    def test_handles_exception(self, mock_collect: MagicMock) -> None:
        mock_collect.side_effect = RuntimeError("API down")
        main_mod._poll_and_store()  # should not raise
