import re
from datetime import datetime, timedelta

def parse_booking_datetime(message_text):
    patterns = [
        r'^(\d{2})\.(\d{2})\s(\d{2})[:.:](\d{2})(?:\s(\d+))?$',  # dd.mm hh:mm or dd.mm hh.mm (with optional number of places)
        r'^(\d{2})\.(\d{2})\s(\d{4})(?:\s(\d+))?$',  # dd.mm hhmm (with optional number of places)
        r'^(\d{2})/(\d{2})\s(\d{2})[:.:](\d{2})(?:\s(\d+))?$',  # dd/mm hh:mm or dd/mm hh.mm (with optional number of places)
        r'^(\d{2})/(\d{2})\s(\d{4})(?:\s(\d+))?$',  # dd/mm hhmm (with optional number of places)
        r'^(\d{2})\s(\d{2}):(\d{2})(?:\s(\d+))?$',  # dd hh:mm (with optional number of places)
        r'^(\d{2})\s(\d{2})\.(\d{2})(?:\s(\d+))?$',  # dd hh.mm (with optional number of places)
        r'^(\d{2})\s(\d{4})(?:\s(\d+))?$',  # dd hhmm (with optional number of places)
        r'^(\d{4})(?:\s(\d+))?$',  # hhmm (with optional number of places)
        r'^(\d{2})[:.:](\d{2})(?:\s(\d+))?$'  # hh:mm or hh.mm (with optional number of places)
    ]
    
    current_date = datetime.now()
    
    for pattern in patterns:
        match = re.match(pattern, message_text)
        if match:
            groups = match.groups()
            
            try:
                if len(groups) == 5:  # dd.mm hh:mm or dd.mm hh.mm or dd/mm hh:mm or dd/mm hh.mm (with optional number of places)
                    day, month, hour, minute, places = groups
                    year = current_date.year
                elif len(groups) == 4:
                    if ':' in message_text or '.' in message_text:  # dd hh:mm or dd hh.mm (with optional number of places)
                        day, hour, minute, places = groups
                        month, year = current_date.month, current_date.year
                    else:  # dd.mm hhmm or dd/mm hhmm (with optional number of places)
                        day, month, time, places = groups
                        hour, minute = divmod(int(time), 100)
                        year = current_date.year
                elif len(groups) == 3:  # dd hhmm or hh:mm or hh.mm (with optional number of places)
                    if ':' in message_text or '.' in message_text:  # hh:mm or hh.mm (with optional number of places)
                        hour, minute, places = groups
                        day, month, year = current_date.day, current_date.month, current_date.year
                        booking_datetime = datetime(year, month, day, int(hour), int(minute))
                        if booking_datetime <= current_date:
                            booking_datetime += timedelta(days=1)
                    else:  # dd hhmm (with optional number of places)
                        day, time, places = groups
                        hour, minute = divmod(int(time), 100)
                        month, year = current_date.month, current_date.year
                else:  # hhmm (with optional number of places)
                    time, places = groups
                    hour, minute = divmod(int(time), 100)
                    day, month, year = current_date.day, current_date.month, current_date.year
                
                if 'booking_datetime' not in locals():
                    booking_datetime = datetime(year, int(month), int(day), int(hour), int(minute))
                
                places = int(places) if places else 1  # Default to 1 place if not specified
                
                return booking_datetime, places
            
            except ValueError:
                return None, None
    
    return None, None