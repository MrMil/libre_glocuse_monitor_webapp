from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from dataclasses import asdict
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.db import get_all_readings, get_readings_in_range, init_db, upsert_readings
from app.libre import (
    GlucoseThresholds,
    GraphPoint,
    collect_readings,
    get_current_reading,
    get_graph_data,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

POLL_INTERVAL_SECONDS = 60

_cached_thresholds: GlucoseThresholds | None = None


def _poll_and_store() -> None:
    """Fetch latest readings from LibreLinkUp and store them in the database."""
    global _cached_thresholds
    try:
        rows, thresholds = collect_readings()
        inserted = upsert_readings(rows)
        _cached_thresholds = thresholds
        logger.info("Poll: %d readings fetched, %d new stored", len(rows), inserted)
    except Exception:
        logger.exception("Poll failed")


async def _background_poller() -> None:
    """Periodically poll LibreLinkUp for new readings."""
    while True:
        await asyncio.to_thread(_poll_and_store)
        await asyncio.sleep(POLL_INTERVAL_SECONDS)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    init_db()
    await asyncio.to_thread(_poll_and_store)
    task = asyncio.create_task(_background_poller())
    yield
    task.cancel()


app = FastAPI(title="Sugar Monitor", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=str(Path(__file__).parent / "static")), name="static")
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))


@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "index.html")


@app.get("/history", response_class=HTMLResponse)
async def history(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "history.html")


@app.get("/api/current")
async def api_current() -> JSONResponse:
    try:
        reading = get_current_reading()
        data: dict[str, Any] = asdict(reading)
        data["timestamp"] = reading.timestamp.isoformat()
        data["trend_name"] = reading.trend.name
        return JSONResponse(content=data)
    except Exception as e:
        logging.exception("Failed to fetch current reading")
        return JSONResponse(content={"error": str(e)}, status_code=500)


@app.get("/api/graph")
async def api_graph() -> JSONResponse:
    try:
        current, points, thresholds = get_graph_data()
        current_data: dict[str, Any] = asdict(current)
        current_data["timestamp"] = current.timestamp.isoformat()
        current_data["trend_name"] = current.trend.name
        return JSONResponse(
            content={
                "current": current_data,
                "graph": [asdict(p) for p in points],
                "thresholds": asdict(thresholds),
            }
        )
    except Exception as e:
        logging.exception("Failed to fetch graph data")
        return JSONResponse(content={"error": str(e)}, status_code=500)


@app.get("/api/history")
async def api_history(start: str | None = None, end: str | None = None) -> JSONResponse:
    try:
        if start and end:
            rows = await asyncio.to_thread(get_readings_in_range, start, end)
        else:
            rows = await asyncio.to_thread(get_all_readings)
        points = [GraphPoint(value=val, timestamp=ts) for ts, val in rows]

        thresholds = _cached_thresholds or GlucoseThresholds(
            urgent_low=55, target_low=70, target_high=180
        )

        return JSONResponse(
            content={
                "points": [asdict(p) for p in points],
                "thresholds": asdict(thresholds),
            }
        )
    except Exception as e:
        logging.exception("Failed to fetch history data")
        return JSONResponse(content={"error": str(e)}, status_code=500)
