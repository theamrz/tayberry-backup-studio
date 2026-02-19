from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class JalaliDate:
    year: int
    month: int
    day: int


def gregorian_to_jalali(dt: datetime) -> JalaliDate:
    """
    Convert a Gregorian date to Jalali (Persian) date.

    Implementation adapted from widely used Gregorian <-> Jalali
    arithmetic conversions (e.g., Roozbeh Pournader / Mohammad Toosi),
    which operate on day counts relative to the Persian epoch.
    """
    gy = dt.year - 1600
    gm = dt.month - 1
    gd = dt.day - 1

    g_day_no = 365 * gy + (gy + 3) // 4 - (gy + 99) // 100 + (gy + 399) // 400

    g_days_in_month = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    for i in range(gm):
        g_day_no += g_days_in_month[i]
    # leap adjustment
    if gm > 1 and (
        (gy % 4 == 0 and gy % 100 != 0)
        or (gy % 400 == 0)
    ):
        g_day_no += 1
    g_day_no += gd

    j_day_no = g_day_no - 79
    j_np = j_day_no // 12053  # 12053 = 365*33 + 8 leap
    j_day_no %= 12053

    jy = 979 + 33 * j_np + 4 * (j_day_no // 1461)
    j_day_no %= 1461

    if j_day_no >= 366:
        jy += (j_day_no - 1) // 365
        j_day_no = (j_day_no - 1) % 365

    jm = 0
    jd = 0
    jalali_months = [31, 31, 31, 31, 31, 31, 30, 30, 30, 30, 30, 29]
    for i, days_in_month in enumerate(jalali_months):
        if j_day_no < days_in_month:
            jm = i + 1
            jd = j_day_no + 1
            break
        j_day_no -= days_in_month

    return JalaliDate(jy, jm, jd)


def format_jalali_stamp(dt: datetime) -> str:
    """
    Format a datetime as a compact Jalali stamp suitable for filenames.

    Example: 1403-01-15_23-45
    """
    j = gregorian_to_jalali(dt)
    return f"{j.year:04d}-{j.month:02d}-{j.day:02d}_{dt:%H-%M}"


def format_jalali_datetime(dt: datetime) -> str:
    """
    Format a datetime as a human-friendly Jalali date-time string.

    Example: 1403-01-15 23:45:10
    """
    j = gregorian_to_jalali(dt)
    return f"{j.year:04d}-{j.month:02d}-{j.day:02d} {dt:%H:%M:%S}"
