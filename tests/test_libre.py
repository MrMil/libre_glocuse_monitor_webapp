from __future__ import annotations

from datetime import datetime
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from pylibrelinkup import APIUrl
from pylibrelinkup.exceptions import RedirectError
from requests.exceptions import HTTPError

import app.libre as libre
from app.libre import (
    GlucoseReading,
    GraphPoint,
    collect_readings,
    get_current_reading,
    get_graph_data,
)
from tests.conftest import (
    make_glucose_measurement,
    make_glucose_measurement_with_trend,
    make_graph_response,
    make_patient,
)


class TestGlucoseReadingFromMeasurement:
    def test_normal_reading(self) -> None:
        m = make_glucose_measurement_with_trend(120.0)
        r = GlucoseReading.from_measurement(m)
        assert r.value == 120.0
        assert r.value_in_mg_per_dl == 120.0
        assert r.is_high is False
        assert r.is_low is False

    def test_high_reading(self) -> None:
        m = make_glucose_measurement_with_trend(250.0, is_high=True)
        r = GlucoseReading.from_measurement(m)
        assert r.is_high is True

    def test_low_reading(self) -> None:
        m = make_glucose_measurement_with_trend(50.0, is_low=True)
        r = GlucoseReading.from_measurement(m)
        assert r.is_low is True


class TestGraphPointFromMeasurement:
    def test_creates_iso_timestamp(self) -> None:
        ts = datetime(2026, 2, 24, 10, 30, 0)
        m = make_glucose_measurement(115.0, ts)
        p = GraphPoint.from_measurement(m)
        assert p.value == 115.0
        assert p.timestamp == "2026-02-24T10:30:00"


class TestGetClientAndPatient:
    @patch("app.libre.PyLibreLinkUp")
    def test_authenticates_and_returns_patient(self, mock_cls: MagicMock) -> None:
        patient = make_patient()
        instance = mock_cls.return_value
        instance.token = "tok"
        instance.get_patients.return_value = [patient]

        _client, pat = libre._get_client_and_patient()
        instance.authenticate.assert_called_once()
        assert pat is patient

    @patch("app.libre.PyLibreLinkUp")
    def test_caches_client(self, mock_cls: MagicMock) -> None:
        patient = make_patient()
        instance = mock_cls.return_value
        instance.token = "tok"
        instance.get_patients.return_value = [patient]

        c1, _ = libre._get_client_and_patient()
        c2, _ = libre._get_client_and_patient()
        assert c1 is c2
        assert mock_cls.call_count == 1

    @patch("app.libre.PyLibreLinkUp")
    def test_handles_redirect_error(self, mock_cls: MagicMock) -> None:
        patient = make_patient()

        first_instance = MagicMock()
        first_instance.authenticate.side_effect = RedirectError(APIUrl.EU)

        second_instance = MagicMock()
        second_instance.token = "tok"
        second_instance.get_patients.return_value = [patient]

        mock_cls.side_effect = [first_instance, second_instance]

        _, pat = libre._get_client_and_patient()
        assert pat is patient
        assert second_instance.authenticate.called

    @patch("app.libre.PyLibreLinkUp")
    def test_no_patients_raises(self, mock_cls: MagicMock) -> None:
        instance = mock_cls.return_value
        instance.token = "tok"
        instance.get_patients.return_value = []

        with pytest.raises(RuntimeError, match="No patients found"):
            libre._get_client_and_patient()


class TestWithReauth:
    @patch("app.libre._get_client_and_patient")
    def test_calls_fn_normally(self, mock_get: MagicMock) -> None:
        client = MagicMock()
        patient = make_patient()
        mock_get.return_value = (client, patient)

        result = libre._with_reauth(lambda c, p: 42)
        assert result == 42

    @patch("app.libre._get_client_and_patient")
    def test_retries_on_401(self, mock_get: MagicMock) -> None:
        client = MagicMock()
        patient = make_patient()
        mock_get.return_value = (client, patient)

        response = MagicMock()
        response.status_code = 401
        error = HTTPError(response=response)

        call_count = 0

        def fn(c: Any, p: Any) -> str:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise error
            return "ok"

        result = libre._with_reauth(fn)
        assert result == "ok"
        assert call_count == 2

    @patch("app.libre._get_client_and_patient")
    def test_retries_on_403(self, mock_get: MagicMock) -> None:
        client = MagicMock()
        patient = make_patient()
        mock_get.return_value = (client, patient)

        response = MagicMock()
        response.status_code = 403
        error = HTTPError(response=response)

        call_count = 0

        def fn(c: Any, p: Any) -> str:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise error
            return "ok"

        result = libre._with_reauth(fn)
        assert result == "ok"

    @patch("app.libre._get_client_and_patient")
    def test_retries_on_430(self, mock_get: MagicMock) -> None:
        client = MagicMock()
        patient = make_patient()
        mock_get.return_value = (client, patient)

        response = MagicMock()
        response.status_code = 430
        error = HTTPError(response=response)

        call_count = 0

        def fn(c: Any, p: Any) -> str:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise error
            return "ok"

        result = libre._with_reauth(fn)
        assert result == "ok"

    @patch("app.libre._get_client_and_patient")
    def test_raises_non_auth_http_error(self, mock_get: MagicMock) -> None:
        client = MagicMock()
        patient = make_patient()
        mock_get.return_value = (client, patient)

        response = MagicMock()
        response.status_code = 500
        error = HTTPError(response=response)

        def fn(c: Any, p: Any) -> str:
            raise error

        with pytest.raises(HTTPError):
            libre._with_reauth(fn)

    @patch("app.libre._get_client_and_patient")
    def test_raises_http_error_with_no_response(self, mock_get: MagicMock) -> None:
        client = MagicMock()
        patient = make_patient()
        mock_get.return_value = (client, patient)

        error = HTTPError(response=None)

        def fn(c: Any, p: Any) -> str:
            raise error

        with pytest.raises(HTTPError):
            libre._with_reauth(fn)


class TestGetCurrentReading:
    @patch("app.libre._get_client_and_patient")
    def test_returns_reading(self, mock_get: MagicMock) -> None:
        client = MagicMock()
        patient = make_patient()
        mock_get.return_value = (client, patient)

        measurement = make_glucose_measurement_with_trend(130.0)
        client.latest.return_value = measurement

        reading = get_current_reading()
        assert reading.value == 130.0
        client.latest.assert_called_once_with(patient_identifier=patient)


class TestGetGraphData:
    @patch("app.libre._get_client_and_patient")
    def test_returns_current_points_thresholds(self, mock_get: MagicMock) -> None:
        client = MagicMock()
        patient = make_patient()
        mock_get.return_value = (client, patient)

        resp = make_graph_response(
            current_value=150.0,
            graph_values=[100.0, 110.0],
            target_low=70,
            target_high=180,
            urgent_low_th=55,
        )
        client.read.return_value = resp

        current, points, thresholds = get_graph_data()
        assert current.value == 150.0
        assert len(points) == 2
        assert thresholds.target_low == 70
        assert thresholds.target_high == 180
        assert thresholds.urgent_low == 55

    @patch("app.libre._get_client_and_patient")
    def test_urgent_low_defaults_to_55(self, mock_get: MagicMock) -> None:
        client = MagicMock()
        patient = make_patient()
        mock_get.return_value = (client, patient)

        resp = make_graph_response(urgent_low_th=0)
        client.read.return_value = resp

        _, _, thresholds = get_graph_data()
        assert thresholds.urgent_low == 55


class TestCollectReadings:
    @patch("app.libre._get_client_and_patient")
    def test_merges_graph_and_logbook(self, mock_get: MagicMock) -> None:
        client = MagicMock()
        patient = make_patient()
        mock_get.return_value = (client, patient)

        resp = make_graph_response(graph_values=[100.0, 110.0])
        client.read.return_value = resp

        logbook_entry = make_glucose_measurement(90.0, datetime(2026, 2, 23, 12, 0, 0))
        client.logbook.return_value = [logbook_entry]

        rows, _thresholds = collect_readings()
        assert len(rows) == 4  # 1 current + 2 graph + 1 logbook
        timestamps = {r[0] for r in rows}
        assert "2026-02-23T12:00:00" in timestamps

    @patch("app.libre._get_client_and_patient")
    def test_deduplicates_by_timestamp(self, mock_get: MagicMock) -> None:
        client = MagicMock()
        patient = make_patient()
        mock_get.return_value = (client, patient)

        resp = make_graph_response(graph_values=[100.0])
        client.read.return_value = resp

        dup_entry = make_glucose_measurement(100.0, datetime(2026, 2, 24, 8, 0, 0))
        client.logbook.return_value = [dup_entry]

        rows, _ = collect_readings()
        assert len(rows) == 2  # 1 current + 1 graph (logbook is a dup of graph)

    @patch("app.libre._get_client_and_patient")
    def test_empty_logbook(self, mock_get: MagicMock) -> None:
        client = MagicMock()
        patient = make_patient()
        mock_get.return_value = (client, patient)

        resp = make_graph_response(graph_values=[100.0, 110.0, 120.0])
        client.read.return_value = resp
        client.logbook.return_value = []

        rows, _ = collect_readings()
        assert len(rows) == 3  # 1 current + 3 graph (current deduped with graph[2] at 10:00)


class TestReauthOnExpiredToken:
    @patch("app.libre.PyLibreLinkUp")
    def test_reauths_when_token_is_none(self, mock_cls: MagicMock) -> None:
        patient = make_patient()
        instance = mock_cls.return_value
        instance.token = "tok"
        instance.get_patients.return_value = [patient]

        libre._get_client_and_patient()
        instance.token = None
        libre._get_client_and_patient()
        assert mock_cls.call_count == 2
