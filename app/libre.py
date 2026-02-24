from __future__ import annotations

import logging
import threading
import time
import warnings
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, TypeVar

if TYPE_CHECKING:
    from datetime import datetime

from pylibrelinkup import PyLibreLinkUp
from pylibrelinkup.exceptions import RedirectError
from pylibrelinkup.models.data import (
    GlucoseMeasurement,
    GlucoseMeasurementWithTrend,
    Patient,
    Trend,
)
from requests.exceptions import HTTPError

from app.config import settings

T = TypeVar("T")
_CallableFn = Callable[[PyLibreLinkUp, Patient], T]

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Cached, shared client - authenticates once and reuses the session token
# ---------------------------------------------------------------------------

_client: PyLibreLinkUp | None = None
_patient: Patient | None = None
_lock = threading.Lock()
_last_auth_ts: float = 0.0
_AUTH_TTL_SECONDS = 55 * 60  # re-auth after 55 min (tokens last ~60 min)


def _get_client_and_patient() -> tuple[PyLibreLinkUp, Patient]:
    """Return an authenticated client + patient, reusing a cached session."""
    global _client, _patient, _last_auth_ts

    with _lock:
        now = time.monotonic()
        need_auth = (
            _client is None or _client.token is None or now - _last_auth_ts > _AUTH_TTL_SECONDS
        )

        if need_auth:
            logger.info("Authenticating with LibreLinkUp...")
            client = PyLibreLinkUp(
                email=settings.libre_email,
                password=settings.libre_password,
                api_url=settings.api_url,
            )
            try:
                client.authenticate()
            except RedirectError as e:
                logger.info("Redirected to region: %s", e.region)
                client = PyLibreLinkUp(
                    email=settings.libre_email,
                    password=settings.libre_password,
                    api_url=e.region,
                )
                client.authenticate()

            patients = client.get_patients()
            logger.info("Found %d patient(s): %s", len(patients), patients)
            if not patients:
                raise RuntimeError(
                    "No patients found on this LibreLinkUp account. "
                    "Make sure you have set up a sharing connection in the "
                    "FreeStyle Libre app and accepted the invitation in LibreLinkUp."
                )

            _client = client
            _patient = patients[0]
            _last_auth_ts = now

        assert _client is not None
        assert _patient is not None
        return _client, _patient


def _with_reauth[T](fn: _CallableFn[T]) -> T:
    """Run *fn(client, patient)*, retrying once with a fresh session on auth failure."""
    global _client, _last_auth_ts

    client, patient = _get_client_and_patient()
    try:
        return fn(client, patient)
    except HTTPError as e:
        if e.response is not None and e.response.status_code in (401, 403, 430):
            logger.info("Got %s, forcing re-authentication", e.response.status_code)
            with _lock:
                _client = None
                _last_auth_ts = 0.0
            client, patient = _get_client_and_patient()
            return fn(client, patient)
        raise


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class GlucoseThresholds:
    urgent_low: int
    target_low: int
    target_high: int


@dataclass
class GlucoseReading:
    value: float
    value_in_mg_per_dl: float
    trend: Trend
    trend_arrow: str
    timestamp: datetime
    is_high: bool
    is_low: bool

    @classmethod
    def from_measurement(cls, m: GlucoseMeasurementWithTrend) -> GlucoseReading:
        return cls(
            value=m.value,
            value_in_mg_per_dl=m.value_in_mg_per_dl,
            trend=m.trend,
            trend_arrow=m.trend.indicator,
            timestamp=m.timestamp,
            is_high=m.is_high,
            is_low=m.is_low,
        )


@dataclass
class GraphPoint:
    value: float
    timestamp: str

    @classmethod
    def from_measurement(cls, m: GlucoseMeasurement) -> GraphPoint:
        return cls(
            value=m.value,
            timestamp=m.timestamp.isoformat(),
        )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def get_current_reading() -> GlucoseReading:
    def _fetch(client: PyLibreLinkUp, patient: Patient) -> GlucoseReading:
        latest = client.latest(patient_identifier=patient)
        return GlucoseReading.from_measurement(latest)

    return _with_reauth(_fetch)


def get_graph_data() -> tuple[GlucoseReading, list[GraphPoint], GlucoseThresholds]:
    """Fetch current reading, 12h graph, and the patient's target thresholds."""

    def _fetch(
        client: PyLibreLinkUp, patient: Patient
    ) -> tuple[GlucoseReading, list[GraphPoint], GlucoseThresholds]:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            response = client.read(patient_identifier=patient)

        connection = response.data.connection
        urgent_low = connection.alarm_rules.f.th or 55
        thresholds = GlucoseThresholds(
            urgent_low=urgent_low,
            target_low=connection.target_low,
            target_high=connection.target_high,
        )
        logger.info(
            "Patient thresholds: urgent_low=%d, low=%d, high=%d",
            thresholds.urgent_low,
            thresholds.target_low,
            thresholds.target_high,
        )

        current = GlucoseReading.from_measurement(connection.glucose_measurement)
        points = [GraphPoint.from_measurement(m) for m in response.data.graph_data]
        return current, points, thresholds

    return _with_reauth(_fetch)


def collect_readings() -> tuple[list[tuple[str, float]], GlucoseThresholds]:
    """Fetch graph + logbook data from the API and return (timestamp, value) rows + thresholds."""

    def _fetch(
        client: PyLibreLinkUp, patient: Patient
    ) -> tuple[list[tuple[str, float]], GlucoseThresholds]:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            response = client.read(patient_identifier=patient)

        connection = response.data.connection
        urgent_low = connection.alarm_rules.f.th or 55
        thresholds = GlucoseThresholds(
            urgent_low=urgent_low,
            target_low=connection.target_low,
            target_high=connection.target_high,
        )

        rows: list[tuple[str, float]] = []
        seen: set[str] = set()

        current = connection.glucose_measurement
        current_ts = current.timestamp.isoformat()
        seen.add(current_ts)
        rows.append((current_ts, current.value))

        for m in response.data.graph_data:
            ts = m.timestamp.isoformat()
            if ts not in seen:
                seen.add(ts)
                rows.append((ts, m.value))

        logbook = client.logbook(patient_identifier=patient)
        for m in logbook:
            ts = m.timestamp.isoformat()
            if ts not in seen:
                seen.add(ts)
                rows.append((ts, m.value))

        logger.info(
            "Collected 1 current + %d graph + %d logbook = %d unique readings",
            len(response.data.graph_data),
            len(logbook),
            len(rows),
        )
        return rows, thresholds

    return _with_reauth(_fetch)
