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
    parts = re.split(r'\s+', message_text.strip())
    current_date = datetime.now().date()
    
    if len(parts) < 1:
        return None, None
    
    time_part = parts[0]
    amount_part = None
    
    # Check if the last part is 'k' followed by a number
    if len(parts) > 1 and parts[-1].lower().startswith('k'):
        amount_part = parts[-1][1:]  # Remove the 'k' and keep the number
        parts = parts[:-1]  # Remove the last part from parts
    elif len(parts) > 1 and parts[-1].isdigit():
        amount_part = parts[-1]
        parts = parts[:-1]
    
    parsed_time = parse_time(time_part)
    amount = parse_amount(amount_part) if amount_part else 1
    
    if parsed_time is None:
        return None, None
    
    booking_datetime = datetime.combine(current_date, parsed_time)
    
    # If the booking time is in the past, move it to tomorrow
    if booking_datetime <= datetime.now():
        booking_datetime += timedelta(days=1)
    
    return booking_datetime, amount