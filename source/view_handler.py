import pandas as pd
from .data_handler import *
from datetime import datetime, date, timedelta
from collections import defaultdict
from source.user_handler import require_verification


def format_bookings(bookings):
    if not bookings:
        return "No bookings found."

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
        output.append(f"\n{date_str}:")
        for time, count in sorted(time_bookings.items()):
            time_str = time.strftime("%H:%M")
            concept_str = "concept" if count == 1 else "concepts"
            output.append(f"  {time_str} {count} {concept_str}")

    return "\n".join(output)

@require_verification
async def view_bookings(update, context):
    """Shows all booked concepts or bookings for a specific day or user, grouped by time and users."""
    user_input = context.args[0] if context.args else None
    remove_old_bookings()
    bookings = get_all_bookings()

    if not bookings:
        await update.message.reply_text("No bookings found.")
        return

    user_id = update.effective_user.id
    is_my_command = update.message.text.startswith('/my')

    if is_my_command:
        # Filter bookings for the current user
        filtered_bookings = [b for b in bookings if b['user_id'] == user_id]
        if not filtered_bookings:
            await update.message.reply_text("You have no bookings.")
            return
        grouped_bookings = group_bookings(filtered_bookings, include_date=True)
        message = "Your bookings:\n\n"
    elif user_input:
        try:
            current_date = datetime.now()
            if '.' in user_input:
                # Format: dd.mm
                target_date = datetime.strptime(f"{user_input}.{current_date.year}", "%d.%m.%Y").date()
            else:
                # Format: dd
                day = int(user_input)
                target_date = get_target_date(day, current_date)

            filtered_bookings = [b for b in bookings if (b['date'].date() if isinstance(b['date'], datetime) else b['date']) == target_date]
            
            if not filtered_bookings:
                await update.message.reply_text(f"No bookings found for {target_date.strftime('%d.%m')}.")
                return

            grouped_bookings = group_bookings(filtered_bookings, include_date=False)
            message = f"Bookings for {target_date.strftime('%d.%m')}:\n\n"
        except ValueError:
            await update.message.reply_text("Invalid date format. Please use dd.mm or dd")
            return
    else:
        grouped_bookings = group_bookings(bookings, include_date=True)
        message = "All booked concepts:\n\n"

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
                    message += f"{time_slot}: {user_info['count']} concept{'s' if user_info['count'] > 1 else ''}\n"
            else:
                total_count = sum(user_info['count'] for user_info in users.values())
                user_str = ", ".join(f"{user_info['count']}x <a href='{user_info['link']}'>{name}</a>" if user_info['link'] else f"{user_info['count']}x {name}" for name, user_info in users.items())
                message += f"{time_slot}: {total_count} concept{'s' if total_count > 1 else ''} ({user_str})\n"
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
            time_str = booking['time'].strftime('%H:%M')
            user_name, user_link = user_data.get(booking['user_id'], ('Unknown', ''))
            places = booking.get('places', 1)  # Default to 1 if 'places' is not present
            grouped[date_str][time_str][user_name]['count'] += places
            grouped[date_str][time_str][user_name]['link'] = user_link
        return {date: {time: dict(users) for time, users in sorted(time_slots.items())} 
                for date, time_slots in grouped.items()}
    else:
        grouped = defaultdict(lambda: defaultdict(lambda: {'count': 0, 'link': ''}))
        for booking in bookings:
            time_str = booking['time'].strftime('%H:%M')
            user_name, user_link = user_data.get(booking['user_id'], ('Unknown', ''))
            places = booking.get('places', 1)  # Default to 1 if 'places' is not present
            grouped[time_str][user_name]['count'] += places
            grouped[time_str][user_name]['link'] = user_link
        return {time: dict(users) for time, users in sorted(grouped.items())}