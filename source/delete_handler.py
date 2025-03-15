import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext, CallbackQueryHandler
from .data_handler import get_all_bookings, save_bookings, remove_old_bookings
from datetime import datetime, timedelta
from collections import defaultdict
from .view_handler import translate_date_string, get_concept_form

logger = logging.getLogger(__name__)


async def delete_bookings(update: Update, context: CallbackContext):
    remove_old_bookings()
    user_id = update.effective_user.id
    bookings = get_all_bookings()
    user_bookings = [b for b in bookings if b['user_id'] == user_id]

    if not user_bookings:
        await update.message.reply_text("У вас нет активных бронирований.")
        return

    # Group bookings by date and time
    grouped_bookings = defaultdict(list)
    for booking in user_bookings:
        booking_datetime = datetime.combine(booking['date'], booking['time'])
        # Use a tuple of (datetime, duration) as the key to properly group bookings
        duration = booking.get('duration', 60)  # Default to 60 minutes if not specified
        grouped_bookings[(booking_datetime, duration)].append(booking)

    # Sort grouped bookings from nearest to furthest
    sorted_grouped_bookings = sorted(grouped_bookings.items())

    keyboard = []
    for (booking_datetime, duration), bookings_list in sorted_grouped_bookings:
        # Get the count of places for this booking time
        places_count = sum(booking.get('places', 1) for booking in bookings_list)
        
        # Format the button text with translated day name and correct grammar
        date_str = booking_datetime.strftime('%d/%m (%A)')
        date_str = translate_date_string(date_str, short=True)
        time_str = booking_datetime.strftime('%H:%M')
        
        # Include duration in the button text
        end_time = (booking_datetime + timedelta(minutes=duration)).strftime('%H:%M')
        # button_text = f"{date_str} {time_str}-{end_time} ({duration} мин.) - {places_count} {get_concept_form(places_count)}"
        button_text = f"{date_str} {time_str}-{end_time} - {places_count}x"
        print('\n\n', button_text, '\n\n')

        # Include duration in the callback data
        callback_data = f"delete_{booking_datetime.strftime('%Y-%m-%d_%H:%M:%S')}_{duration}"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Выберите какую бронь отменить:", reply_markup=reply_markup)

async def delete_booking_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()

    # Parse the callback data to extract date, time, and duration
    callback_parts = query.data.split('_')
    date_str = callback_parts[1]
    time_str = callback_parts[2]
    # Extract duration if available, otherwise default to 60
    duration = int(callback_parts[3]) if len(callback_parts) > 3 else 60
    
    bookings = get_all_bookings()
    user_id = update.effective_user.id

    # Parse the date and time strings
    date = datetime.strptime(date_str, "%Y-%m-%d").date()
    time = datetime.strptime(time_str, "%H:%M:%S").time()

    # Find the booking to be deleted
    booking_to_delete = None
    for b in bookings:
        if (b['user_id'] == user_id and 
            b['date'] == date and 
            b['time'] == time and 
            b.get('duration', 60) == duration):
            booking_to_delete = b
            break
    
    # Get the number of places in the booking
    places_count = booking_to_delete.get('places', 1) if booking_to_delete else 1

    # Remove the selected booking
    updated_bookings = [b for b in bookings if not (
        b['user_id'] == user_id and 
        b['date'] == date and 
        b['time'] == time and 
        b.get('duration', 60) == duration
    )]

    # Save the updated bookings
    save_bookings(updated_bookings)

    booking_datetime = datetime.combine(date, time)
    formatted_date = booking_datetime.strftime('%d/%m (%A)')
    formatted_date = translate_date_string(formatted_date)
    formatted_time = booking_datetime.strftime('%H:%M')
    end_time = (booking_datetime + timedelta(minutes=duration)).strftime('%H:%M')
    
    await query.edit_message_text(
        f"Ваша бронь на {formatted_date} {formatted_time}-{end_time} "
        f"({duration} мин., {places_count} {get_concept_form(places_count)}) была отменена."
    )

def setup_delete_handlers(application):
    application.add_handler(CallbackQueryHandler(delete_booking_callback, pattern='^delete_'))