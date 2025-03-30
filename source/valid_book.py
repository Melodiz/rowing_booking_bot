from .data_handler import get_gym_timetable, get_gym_closed_periods
from datetime import datetime, time, timedelta


def map_days_to_russian(day_of_week):
    return ['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота', 'Воскресенье'][day_of_week]


def is_valid_booking_time(booking_datetime, places=1, duration=60):
    """Check if the booking time is within the allowed time slots and the gym is not closed."""
    # check the validity of amount of available places
    if places <= 0:
        return False, "Хахахаха, забавно, но мой автор уже подумал об этом)\n \
                        Введите пожалуйста положительное число концептов"
    if booking_datetime <= datetime.now():
        return False, "К сожалению это время уже прошло. Пожалуйста, выберите другое время."
    # First, check if the gym is closed for a specific period
    close_from, close_until = get_gym_closed_periods()
    if close_from != "NaN" and close_until != "NaN":
        try:
            close_from = datetime.strptime(close_from, "%Y-%m-%d %H:%M:%S")
            close_until = datetime.strptime(close_until, "%Y-%m-%d %H:%M:%S")
            if close_from <= booking_datetime < close_until:
                return False, f"Извините, зал закрыт с {close_from.strftime('%d.%m.%Y %H:%M')} до {close_until.strftime('%d.%m.%Y %H:%M')}. - [Администрация]"
        except ValueError:
            return False, "Error: Invalid date format in configuration for gym closure period (plz text to @Mellodizz)"
    # Now check the regular opening hours
    day_of_week = booking_datetime.weekday()
    booking_time_start = booking_datetime.time()
    booking_datetime_end = booking_datetime + timedelta(minutes=duration)
    booking_time_end = booking_datetime_end.time()
    gym_timetable = get_gym_timetable()
    days = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']
    day = days[day_of_week]

    open_time = gym_timetable.get(f'{day}_open')
    close_time = gym_timetable.get(f'{day}_close')
    if open_time == '-1' or close_time == '-1':
        return False, f"Извините, в {map_days_to_russian(day_of_week)} зал на Малой Ордынке 29 не работает."

    try:
        open_time = datetime.strptime(open_time, "%H:%M").time()
        close_time = datetime.strptime(close_time, "%H:%M").time()
    except ValueError:
        return False, f"Error: Invalid time format in gym timetable for {map_days_to_russian(day_of_week)}"
    try:
        if open_time <= booking_time_start and booking_time_end <= close_time:
            return True, ""
        else:
            return False, f"В {map_days_to_russian(day_of_week)} бронирование доступно только с {open_time.strftime('%H:%M')} до {(datetime.combine(datetime.min, close_time) - timedelta(hours=1)).time().strftime('%H:%M')}. Зал на МО29 до {close_time.strftime('%H:%M')}"
    except ValueError:
        return False, f"Error: Invalid time format in gym timetable for {map_days_to_russian(day_of_week)}"
