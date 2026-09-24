from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

UTC = timezone.utc
WEEKDAYS = ["segunda-feira", "terça-feira", "quarta-feira", "quinta-feira", "sexta-feira", "sábado", "domingo"]
WEEKDAYS_SHORT = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]


def utcnow() -> datetime:
    return datetime.now(UTC)


def to_local(dt: datetime, tzname: str) -> datetime:
    return dt.astimezone(ZoneInfo(tzname))


def local_day_range(day: date, tzname: str) -> tuple[datetime, datetime]:
    tz = ZoneInfo(tzname)
    start = datetime.combine(day, time.min, tz)
    return start.astimezone(UTC), (start + timedelta(days=1)).astimezone(UTC)


def fmt_hora(dt: datetime) -> str:
    return f"{dt.hour}h" if dt.minute == 0 else f"{dt.hour}h{dt.minute:02d}"


def fmt_data_curta(dt: datetime) -> str:
    return f"{WEEKDAYS_SHORT[dt.weekday()]}, {dt.day:02d}/{dt.month:02d}"


def fmt_data_extenso(dt: datetime) -> str:
    return f"{WEEKDAYS[dt.weekday()]} ({dt.day:02d}/{dt.month:02d})"


def local_to_utc(day: date, hhmm: str, tzname: str) -> datetime:
    return datetime.combine(day, time.fromisoformat(hhmm), ZoneInfo(tzname)).astimezone(UTC)
