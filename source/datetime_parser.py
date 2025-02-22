import re
from datetime import datetime, timedelta
from .view_handler import get_target_date


def parse_date(date_str, current_date):
    date_patterns = [
        r'^(\d{2})\.(\d{2})$',  # dd.mm
        r'^(\d{2})/(\d{2})$',  # dd/mm
        r'^(\d{2})$'  # dd
    ]

    for pattern in date_patterns:
        match = re.match(pattern, date_str)
        if match:
            groups = match.groups()
            if len(groups) == 2:  # dd.mm or dd/mm
                day, month = map(int, groups)
                year = current_date.year
            else:  # dd
                day = int(groups[0])
                if day <= 0 or day > 31:
                    return None
                target_date = get_target_date(day, current_date)
                month, year = target_date.month, target_date.year

            try:
                return datetime(year, month, day).date()
            except ValueError:
                return None

    return None


def parse_time(time_str):
    time_patterns = [
        r'^(\d{2})[:.:](\d{2})$',  # hh:mm or hh.mm
        r'^(\d{4})$',  # hhmm
    ]

    for pattern in time_patterns:
        match = re.match(pattern, time_str)
        if match:
            groups = match.groups()
            if len(groups) == 2:  # hh:mm or hh.mm
                hour, minute = map(int, groups)
            else:  # hhmm
                hour, minute = divmod(int(groups[0]), 100)

            try:
                return datetime.now().replace(hour=hour, minute=minute, second=0, microsecond=0).time()
            except ValueError:
                return None

    return None


def parse_amount(amount_str):
    try:
        return int(amount_str)
    except ValueError:
        return 1  # Default to 1 if not specified or invalid


def parse_booking_datetime(message_text):
    current_date = datetime.now().date()
    parts = message_text.split()
    if len(parts) < 1:
        return None, None
    if len(parts) == 1:
        parsed_time = parse_time(parts[0])
        if parsed_time is None:
            return None, None
        return datetime.combine(current_date, parsed_time), 1
    if len(parts) == 2:
        if (len(parts[0]) >= 4 and len(parts[1]) == 1):
            parsed_time = parse_time(parts[0])
            if parsed_time is None:
                return None, None
            booking_datetime = datetime.combine(
                current_date, parsed_time)
            parsed_amount = parse_amount(parts[1])
            if parsed_amount <= 0: return None, None
            return booking_datetime, parsed_amount
        else:
            parsed_date = parse_date(parts[0], current_date)
            parsed_time = parse_time(parts[1])
            if parsed_date is None or parsed_time is None:
                return None, None
            return datetime.combine(parsed_date, parsed_time), 1
    if len(parts) == 3:
        parsed_time = parse_time(parts[1])
        parsed_amount = parse_amount(parts[2])
        parsed_date = parse_date(parts[0], current_date)
        if parsed_time is None or parsed_amount <= 0 or parsed_date is None:
            return None, None
        booking_datetime = datetime.combine(parsed_date, parsed_time)
        return booking_datetime, parsed_amount

    return None, None
