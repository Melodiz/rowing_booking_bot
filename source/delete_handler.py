from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext, CallbackQueryHandler
from .data_handler import get_all_bookings, save_bookings, remove_old_bookings
from datetime import datetime

async def delete_bookings(update: Update, context: CallbackContext):
    remove_old_bookings()
    user_id = update.effective_user.id
    bookings = get_all_bookings()
    user_bookings = [b for b in bookings if b['user_id'] == user_id]

    if not user_bookings:
        await update.message.reply_text("You don't have any bookings.")
        return

    # Sort user_bookings from nearest to furthest
    sorted_bookings = sorted(user_bookings, key=lambda b: datetime.combine(b['date'], b['time']))

    keyboard = []
    for booking in sorted_bookings:
        booking_datetime = datetime.combine(booking['date'], booking['time'])
        button_text = booking_datetime.strftime('%d/%m %H:%M (%A)')
        callback_data = f"delete_{booking['date'].strftime('%Y-%m-%d')}_{booking['time'].strftime('%H:%M:%S')}"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Select a booking to delete:", reply_markup=reply_markup)

async def delete_booking_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()

    _, date_str, time_str = query.data.split('_', 2)
    bookings = get_all_bookings()
    user_id = update.effective_user.id

    # Parse the date and time strings
    date = datetime.strptime(date_str, "%Y-%m-%d").date()
    time = datetime.strptime(time_str, "%H:%M:%S").time()

    # Remove the selected booking
    updated_bookings = [b for b in bookings if not (b['user_id'] == user_id and b['date'] == date and b['time'] == time)]

    # Save the updated bookings
    save_bookings(updated_bookings)

    booking_datetime = datetime.combine(date, time)
    formatted_datetime = booking_datetime.strftime('%d/%m %H:%M (%A)')
    await query.edit_message_text(f"Your booking for {formatted_datetime} has been deleted.")

def setup_delete_handlers(application):
    application.add_handler(CallbackQueryHandler(delete_booking_callback, pattern='^delete_'))