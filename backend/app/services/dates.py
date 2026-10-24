from datetime import date, timedelta


def monday_of(value: date) -> date:
    return value - timedelta(days=value.weekday())


def week_days(week_start: date) -> list[date]:
    start = monday_of(week_start)
    return [start + timedelta(days=i) for i in range(7)]


def is_weekend(value: date) -> bool:
    return value.weekday() >= 5
