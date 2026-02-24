from __future__ import annotations

from app.db import get_all_readings, get_readings_in_range, init_db, upsert_readings


class TestInitDb:
    def test_creates_table(self, tmp_db: str) -> None:
        init_db()
        init_db()  # idempotent

    def test_upsert_after_init(self, tmp_db: str) -> None:
        init_db()
        n = upsert_readings([("2026-02-24T10:00:00", 120.0)])
        assert n == 1


class TestUpsertReadings:
    def test_empty_list_returns_zero(self, tmp_db: str) -> None:
        init_db()
        assert upsert_readings([]) == 0

    def test_inserts_new_rows(self, tmp_db: str) -> None:
        init_db()
        rows = [
            ("2026-02-24T10:00:00", 100.0),
            ("2026-02-24T11:00:00", 110.0),
        ]
        assert upsert_readings(rows) == 2

    def test_ignores_duplicate_timestamps(self, tmp_db: str) -> None:
        init_db()
        rows = [("2026-02-24T10:00:00", 100.0)]
        upsert_readings(rows)
        n = upsert_readings(rows)
        assert n == 0

    def test_mixed_new_and_duplicate(self, tmp_db: str) -> None:
        init_db()
        upsert_readings([("2026-02-24T10:00:00", 100.0)])
        rows = [
            ("2026-02-24T10:00:00", 100.0),
            ("2026-02-24T11:00:00", 110.0),
        ]
        n = upsert_readings(rows)
        assert n == 1


class TestGetAllReadings:
    def test_empty_table(self, tmp_db: str) -> None:
        init_db()
        assert get_all_readings() == []

    def test_returns_newest_first(self, tmp_db: str) -> None:
        init_db()
        upsert_readings(
            [
                ("2026-02-24T08:00:00", 80.0),
                ("2026-02-24T12:00:00", 120.0),
                ("2026-02-24T10:00:00", 100.0),
            ]
        )
        readings = get_all_readings()
        assert len(readings) == 3
        assert readings[0][0] == "2026-02-24T12:00:00"
        assert readings[-1][0] == "2026-02-24T08:00:00"

    def test_returns_correct_values(self, tmp_db: str) -> None:
        init_db()
        upsert_readings([("2026-02-24T10:00:00", 123.4)])
        readings = get_all_readings()
        assert readings[0] == ("2026-02-24T10:00:00", 123.4)


class TestGetReadingsInRange:
    def test_empty_table(self, tmp_db: str) -> None:
        init_db()
        assert get_readings_in_range("2026-02-24", "2026-02-25") == []

    def test_filters_by_range(self, tmp_db: str) -> None:
        init_db()
        upsert_readings(
            [
                ("2026-02-23T08:00:00", 80.0),
                ("2026-02-24T08:00:00", 100.0),
                ("2026-02-24T12:00:00", 120.0),
                ("2026-02-25T08:00:00", 140.0),
            ]
        )
        readings = get_readings_in_range("2026-02-24", "2026-02-25")
        assert len(readings) == 2
        assert all(r[0].startswith("2026-02-24") for r in readings)

    def test_returns_newest_first(self, tmp_db: str) -> None:
        init_db()
        upsert_readings(
            [
                ("2026-02-24T08:00:00", 80.0),
                ("2026-02-24T12:00:00", 120.0),
            ]
        )
        readings = get_readings_in_range("2026-02-24", "2026-02-25")
        assert readings[0][0] == "2026-02-24T12:00:00"
        assert readings[1][0] == "2026-02-24T08:00:00"

    def test_start_inclusive_end_exclusive(self, tmp_db: str) -> None:
        init_db()
        upsert_readings(
            [
                ("2026-02-24T00:00:00", 100.0),
                ("2026-02-25T00:00:00", 200.0),
            ]
        )
        readings = get_readings_in_range("2026-02-24", "2026-02-25")
        assert len(readings) == 1
        assert readings[0][0] == "2026-02-24T00:00:00"
