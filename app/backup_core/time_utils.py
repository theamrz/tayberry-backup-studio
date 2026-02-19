from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional
from zoneinfo import ZoneInfo

import logging
import requests


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TimeResult:
    dt: datetime
    source: str


def _parse_iso_datetime(value: str, tz: ZoneInfo) -> datetime:
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(tz)


def _get_time_worldtimeapi(timezone_name: str) -> Optional[TimeResult]:
    url = f"https://worldtimeapi.org/api/timezone/{timezone_name}"
    try:
        resp = requests.get(url, timeout=5)
        resp.raise_for_status()
        data = resp.json()
        dt = _parse_iso_datetime(data["utc_datetime"], ZoneInfo(timezone_name))
        return TimeResult(dt=dt, source="worldtimeapi.org")
    except Exception as exc:  # noqa: BLE001
        logger.debug("worldtimeapi.org failed: %s", exc)
        return None


def _get_time_timeapi_io(timezone_name: str) -> Optional[TimeResult]:
    url = f"https://timeapi.io/api/Time/current/zone?timeZone={timezone_name}"
    try:
        resp = requests.get(url, timeout=5)
        resp.raise_for_status()
        data = resp.json()
        # timeapi.io returns a structured date/time; we build a datetime
        dt = datetime(
            year=int(data["year"]),
            month=int(data["month"]),
            day=int(data["day"]),
            hour=int(data["hour"]),
            minute=int(data["minute"]),
            second=int(data["seconds"]),
            tzinfo=ZoneInfo(timezone_name),
        )
        return TimeResult(dt=dt, source="timeapi.io")
    except Exception as exc:  # noqa: BLE001
        logger.debug("timeapi.io failed: %s", exc)
        return None


def _get_time_google_header(timezone_name: str) -> Optional[TimeResult]:
    url = "https://www.google.com"
    try:
        resp = requests.get(url, timeout=5)
        resp.raise_for_status()
        date_header = resp.headers.get("Date")
        if not date_header:
            return None
        dt = datetime.strptime(date_header, "%a, %d %b %Y %H:%M:%S %Z")
        dt = dt.replace(tzinfo=timezone.utc).astimezone(ZoneInfo(timezone_name))
        return TimeResult(dt=dt, source="google-header")
    except Exception as exc:  # noqa: BLE001
        logger.debug("Google date header failed: %s", exc)
        return None


def get_current_time(timezone_name: str, use_network_time: bool) -> TimeResult:
    """
    Get the current time in the given timezone.

    When use_network_time is True, it will attempt multiple sources in order:
    1) worldtimeapi.org
    2) timeapi.io
    3) Google Date header
    and fall back to local system time if all fail.
    """
    tz = ZoneInfo(timezone_name)

    if use_network_time:
        for getter in (_get_time_worldtimeapi, _get_time_timeapi_io, _get_time_google_header):
            result = getter(timezone_name)
            if result is not None:
                return result

    # Fallback: system time
    local_dt = datetime.now(tz)
    return TimeResult(dt=local_dt, source="system")
