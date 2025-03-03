import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext, CallbackQueryHandler
from .data_handler import get_all_bookings, save_bookings, remove_old_bookings
from datetime import datetime
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
        grouped_bookings[booking_datetime].append(booking)

    # Sort grouped bookings from nearest to furthest
    sorted_grouped_bookings = sorted(grouped_bookings.items())

    keyboard = []
    for booking_datetime, bookings_list in sorted_grouped_bookings:
        # Get the count of places for this booking time
        places_count = sum(booking.get('places', 1) for booking in bookings_list)
        
        # Format the button text with translated day name and correct grammar
        date_str = booking_datetime.strftime('%d/%m (%A)')
        date_str = translate_date_string(date_str)
        time_str = booking_datetime.strftime('%H:%M')
        
        button_text = f"{date_str} {time_str} - {places_count} {get_concept_form(places_count)}"
        callback_data = f"delete_{booking_datetime.strftime('%Y-%m-%d_%H:%M:%S')}"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Выберите какую бронь отменить:", reply_markup=reply_markup)

async def delete_booking_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()

    _, date_str, time_str = query.data.split('_', 2)
    bookings = get_all_bookings()
    user_id = update.effective_user.id

    # Parse the date and time strings
    date = datetime.strptime(date_str, "%Y-%m-%d").date()
    time = datetime.strptime(time_str, "%H:%M:%S").time()

    # Find the booking to be deleted
    booking_to_delete = None
    for b in bookings:
        if b['user_id'] == user_id and b['date'] == date and b['time'] == time:
            booking_to_delete = b
            break
    
    # Get the number of places in the booking
    places_count = booking_to_delete.get('places', 1) if booking_to_delete else 1

    # Remove the selected booking
    updated_bookings = [b for b in bookings if not (b['user_id'] == user_id and b['date'] == date and b['time'] == time)]

    # Save the updated bookings
    save_bookings(updated_bookings)

    booking_datetime = datetime.combine(date, time)
    formatted_date = booking_datetime.strftime('%d/%m (%A)')
    formatted_date = translate_date_string(formatted_date)
    formatted_time = booking_datetime.strftime('%H:%M')
    
    await query.edit_message_text(
        f"Ваша бронь на {formatted_date} {formatted_time} "
        f"({places_count} {get_concept_form(places_count)}) была отменена."
    )

def setup_delete_handlers(application):
    application.add_handler(CallbackQueryHandler(delete_booking_callback, pattern='^delete_'))