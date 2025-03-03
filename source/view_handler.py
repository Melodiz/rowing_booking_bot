import pandas as pd
from .data_handler import *
from datetime import datetime, date, timedelta
from collections import defaultdict
from source.user_handler import require_verification
import re

# Dictionary to map English day names to Russian day names
WEEKDAY_TRANSLATION = {
    'Monday': 'Понедельник',
    'Tuesday': 'Вторник',
    'Wednesday': 'Среда',
    'Thursday': 'Четверг',
    'Friday': 'Пятница',
    'Saturday': 'Суббота',
    'Sunday': 'Воскресенье'
}

def translate_date_string(date_str):
    """Translate day names in date strings from English to Russian."""
    for eng, rus in WEEKDAY_TRANSLATION.items():
        if eng in date_str:
            return date_str.replace(eng, rus)
    return date_str

def get_concept_form(count):
    """Return the correct grammatical form of the word 'концепт' based on count."""
    if count % 10 == 1 and count % 100 != 11:
        return "концепт"
    elif 2 <= count % 10 <= 4 and (count % 100 < 10 or count % 100 >= 20):
        return "концепта"
    else:
        return "концептов"

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


def format_bookings(bookings):
    if not bookings:
        return "Бронирований не найдено."

    # Sort bookings by date and time
    sorted_bookings = sorted(bookings, key=lambda x: (x['date'], x['time']))

    # Group bookings by date and time
    grouped_bookings = defaultdict(lambda: defaultdict(int))
    for booking in sorted_bookings:
        date = booking['date']
        time = booking['time']
        grouped_bookings[date][time] += 1

    # Format the output
    output = []
    for date, time_bookings in grouped_bookings.items():
        date_str = date.strftime("%d.%m (%A)")
        date_str = translate_date_string(date_str)  # Translate day name to Russian
        output.append(f"\n{date_str}:")
        for time, count in sorted(time_bookings.items()):
            time_str = time.strftime("%H:%M")
            concept_str = get_concept_form(count)
            output.append(f"  {time_str} {count} {concept_str}")

    return "\n".join(output)
@require_verification
async def view_bookings(update, context):
    """Shows all booked concepts or bookings for a specific day or user, grouped by time and users."""
    user_input = context.args[0] if context.args else None
    remove_old_bookings()
    bookings = get_all_bookings()

    if not bookings:
        await update.message.reply_text("Бронирований не найдено.")
        return

    user_id = update.effective_user.id
    is_my_command = update.message.text.startswith('/my')

    if is_my_command:
        # Filter bookings for the current user
        filtered_bookings = [b for b in bookings if b['user_id'] == user_id]
        if not filtered_bookings:
            await update.message.reply_text("У вас нет бронирований.")
            return
        grouped_bookings = group_bookings(filtered_bookings, include_date=True)
        message = "Ваши бронирования:\n\n"

    elif user_input:
        target_date = parse_date(user_input, datetime.now().date())
        if not target_date:
            await update.message.reply_text("Неверный формат даты. Пожалуйста, используйте дд.мм или дд")
            return
        filtered_bookings = [b for b in bookings if (b['date'].date() if isinstance(b['date'], datetime) else b['date']) == target_date]
        grouped_bookings = group_bookings(filtered_bookings, include_date=False)
        message = f"Бронирования на {target_date.strftime('%d.%m')}:\n\n"

    else:
        grouped_bookings = group_bookings(bookings, include_date=True)
        message = "Все забронированные концепты:\n\n"

    # Sort dates from nearest to farthest
    today = date.today()
    sorted_dates = sorted(grouped_bookings.keys(), key=lambda x: abs((datetime.strptime(x.split()[0], '%d/%m').replace(year=today.year).date() - today).days))

    for date_str in sorted_dates:
        message += f"{date_str}\n"
        for time_slot, users in grouped_bookings[date_str].items():
            if is_my_command:
                # For /my command, we only need to show the user's own bookings
                user_info = users.get(get_user_name(user_id), {'count': 0, 'link': ''})
                if user_info['count'] > 0:
                    message += f"{time_slot}: {user_info['count']} {get_concept_form(user_info['count'])}\n"
            else:
                total_count = sum(user_info['count'] for user_info in users.values())
                user_str = ", ".join(f"{user_info['count']}x <a href='{user_info['link']}'>{name}</a>" if user_info['link'] else f"{user_info['count']}x {name}" for name, user_info in users.items())
                message += f"{time_slot}: {total_count} {get_concept_form(total_count)} ({user_str})\n"
        message += "\n"

    await update.message.reply_text(message, parse_mode='HTML', disable_web_page_preview=True)
def get_target_date(day, current_date):
    """Calculate the target date based on the given day and current date."""
    if day >= current_date.day:
        # If the day is in the future, use the current month
        return date(current_date.year, current_date.month, day)
    else:
        # If the day has passed, use the next month
        next_month = current_date.replace(day=1) + timedelta(days=32)
        return date(next_month.year, next_month.month, day)

def group_bookings(bookings, include_date=True):
    """Group bookings by date and time, returning a count for each slot with user information."""
    user_data = get_user_data()
    if include_date:
        grouped = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: {'count': 0, 'link': ''})))
        for booking in bookings:
            date_str = booking['date'].strftime('%d/%m (%A)')
            date_str = translate_date_string(date_str)  # Translate day name to Russian
            time_str = booking['time'].strftime('%H:%M')
            user_name, user_link = user_data.get(booking['user_id'], ('Неопознанная Капибара', ''))
            places = booking.get('places', 1)  # Default to 1 if 'places' is not present
            grouped[date_str][time_str][user_name]['count'] += places
            grouped[date_str][time_str][user_name]['link'] = user_link
        return {date: {time: dict(users) for time, users in sorted(time_slots.items())} 
                for date, time_slots in grouped.items()}
    else:
        grouped = defaultdict(lambda: defaultdict(lambda: {'count': 0, 'link': ''}))
        for booking in bookings:
            time_str = booking['time'].strftime('%H:%M')
            user_name, user_link = user_data.get(booking['user_id'], ('Неопознанная Капибара', ''))
            places = booking.get('places', 1)  # Default to 1 if 'places' is not present
            grouped[time_str][user_name]['count'] += places
            grouped[time_str][user_name]['link'] = user_link
        print(f'\n\n\n { {time: dict(users) for time, users in sorted(grouped.items())}}\n\n\n')
        return {time: dict(users) for time, users in sorted(grouped.items())}