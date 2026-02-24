from __future__ import annotations

import os
from datetime import datetime
from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock, patch
from uuid import UUID

import pytest

if TYPE_CHECKING:
    from collections.abc import Generator

os.environ.setdefault("LIBRE_EMAIL", "test@example.com")
os.environ.setdefault("LIBRE_PASSWORD", "testpass")
os.environ.setdefault("LIBRE_REGION", "US")


@pytest.fixture(autouse=True)
def _reset_libre_cache() -> Generator[None, None, None]:
    """Reset the cached client/patient between tests."""
    import app.libre as libre

    old_client = libre._client
    old_patient = libre._patient
    old_ts = libre._last_auth_ts
    libre._client = None
    libre._patient = None
    libre._last_auth_ts = 0.0
    yield
    libre._client = old_client
    libre._patient = old_patient
    libre._last_auth_ts = old_ts


@pytest.fixture()
def tmp_db(tmp_path: Any) -> Generator[str, None, None]:
    """Provide a temporary SQLite database path and patch DB_PATH to use it."""
    db_path = tmp_path / "test.db"
    with patch("app.db.DB_PATH", db_path):
        yield str(db_path)


def make_patient(
    patient_id: str = "00000000-0000-0000-0000-000000000001",
) -> MagicMock:
    p = MagicMock()
    p.id = UUID(patient_id)
    p.patient_id = UUID(patient_id)
    p.first_name = "Test"
    p.last_name = "User"
    return p


def make_glucose_measurement(
    value: float = 120.0,
    timestamp: datetime | None = None,
    is_high: bool = False,
    is_low: bool = False,
) -> MagicMock:
    ts = timestamp or datetime(2026, 2, 24, 10, 0, 0)
    m = MagicMock()
    m.value = value
    m.value_in_mg_per_dl = value
    m.timestamp = ts
    m.factory_timestamp = ts
    m.measurement_color = 0
    m.glucose_units = 0
    m.type = 0
    m.is_high = is_high
    m.is_low = is_low
    return m


def make_glucose_measurement_with_trend(
    value: float = 120.0,
    timestamp: datetime | None = None,
    is_high: bool = False,
    is_low: bool = False,
    trend: Any = None,
) -> MagicMock:
    from pylibrelinkup.models.data import Trend

    m = make_glucose_measurement(value, timestamp, is_high, is_low)
    m.trend = trend or Trend.STABLE
    return m


def make_graph_response(
    current_value: float = 120.0,
    graph_values: list[float] | None = None,
    target_low: int = 70,
    target_high: int = 180,
    urgent_low_th: int = 55,
) -> MagicMock:
    if graph_values is None:
        graph_values = [100.0, 110.0, 120.0]

    current = make_glucose_measurement_with_trend(current_value)

    graph_data = []
    for i, v in enumerate(graph_values):
        graph_data.append(make_glucose_measurement(v, datetime(2026, 2, 24, 8 + i, 0, 0)))

    alarm_rules = MagicMock()
    alarm_rules.f.th = urgent_low_th

    connection = MagicMock()
    connection.target_low = target_low
    connection.target_high = target_high
    connection.alarm_rules = alarm_rules
    connection.glucose_measurement = current

    data = MagicMock()
    data.connection = connection
    data.graph_data = graph_data

    response = MagicMock()
    response.data = data
    return response
