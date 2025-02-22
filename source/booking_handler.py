import logging
from datetime import datetime, time
from .data_handler import load_bookings, get_available_places, get_user_bookings, add_booking, get_user_name, get_all_bookings
from .datetime_parser import parse_booking_datetime
from .user_handler import is_user_verified
from telegram.ext import CallbackContext
from telegram import Update

logger = logging.getLogger(__name__)
MAX_BOOKINGS_PER_HOUR = 6

async def process_booking_request(update: Update, context: CallbackContext):
    """Process a booking request."""
    user_id = update.effective_user.id
    
    # Check if the user is verified
    if not is_user_verified(user_id):
        await update.message.reply_text("You need to be verified to book a concept. Please use the /verify command.")
        return

    message_text = update.message.text
    
    booking_datetime, places = parse_booking_datetime(message_text)
    
    if booking_datetime is None:
        await update.message.reply_text("Invalid format. Please use one of these formats:\n"
                                        "dd.mm hh:mm [number_of_places]\n"
                                        "dd/mm hh:mm [number_of_places]\n"
                                        "dd hh:mm [number_of_places]\n"
                                        "For example: 25.06 19:30 or 25/06 19:30 3 or 25 19:30 2")
        return
    
    if places <= 0:
        await update.message.reply_text("Haha, very funny. Please book a positive number of concepts.")
        return
    
    if booking_datetime <= datetime.now():
        await update.message.reply_text("Sorry, you can't book for a past date and time.")
        return
    
    # Check if the booking time is valid
    is_valid, error_message = is_valid_booking_time(booking_datetime)
    if not is_valid:
        await update.message.reply_text(error_message)
        return
    
    # Load the latest booking data
    load_bookings()
    
    # Check available space
    available_space = get_available_places(booking_datetime)
    
    if available_space >= places:
        # Attempt to add the booking
        success = add_booking(user_id, booking_datetime)
        if success:
            await update.message.reply_text(f"Your booking for {booking_datetime.strftime('%d.%m at %H:%M')} for {places} place{'s' if places > 1 else ''} has been confirmed!")
        else:
            await update.message.reply_text("Sorry, there was an error while processing your booking. Please try again later.")
    else:
        if available_space > 0:
            await update.message.reply_text(f"Sorry, there are only {available_space} place(s) available for that time slot. Would you like to book the available places? (Yes/No)")
            context.user_data['pending_booking'] = {
                'datetime': booking_datetime,
                'places': available_space
            }
        else:
            await update.message.reply_text("Sorry, there's no available space for that time slot. Please try another time.")


def is_valid_booking_time(booking_datetime):
    """Check if the booking time is within the allowed time slots."""
    day_of_week = booking_datetime.weekday()
    booking_time = booking_datetime.time()

    if day_of_week == 6:  # Sunday (0 is Monday, 6 is Sunday)
        return False, "Sorry, we're closed on Sundays."
    
    if day_of_week == 5:  # Saturday
        if time(8, 0) <= booking_time < time(20, 0):
            return True, ""
        else:
            return False, "On Saturdays, bookings are only available from 8:00 to 19:00."
    
    else:  # Monday to Friday
        if time(8, 0) <= booking_time < time(21, 0):
            return True, ""
        else:
            return False, "On weekdays, bookings are only available from 8:00 to 20:00."

async def book_table(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if not is_user_verified(user_id):
        await update.message.reply_text("You need to be verified to book a concept. Please use the /verify command.")
        return

    message_text = update.message.text
    
    # Load the latest booking data
    load_bookings()
    
    booking_datetime, places = parse_booking_datetime(message_text)
    
    if booking_datetime is None:
        await update.message.reply_text("Invalid format. Please use one of these formats:\n"
                                        "dd.mm hh:mm [number_of_places]\n"
                                        "dd/mm hh:mm [number_of_places]\n"
                                        "dd hh:mm [number_of_places]\n"
                                        "For example: 25.06 19:30 or 25/06 19:30 3 or 25 19:30 2")
        return
    
    if places <= 0:
        await update.message.reply_text("Hahahaha, very funny, but you can book only a positive number of concepts.")
        return
    
    if booking_datetime <= datetime.now():
        await update.message.reply_text("Sorry, you can't book for a past date and time.")
        return
    
    # Check if the booking time is valid
    is_valid, error_message = is_valid_booking_time(booking_datetime)
    if not is_valid:
        await update.message.reply_text(error_message)
        return
    
    available_space = get_available_places(booking_datetime)
    
    if available_space < places:
        if available_space > 0:
            await update.message.reply_text(f"Sorry, there are only {available_space} place(s) available for that time slot. Would you like to book the available places? (Yes/No)")
            context.user_data['pending_booking'] = {
                'datetime': booking_datetime,
                'places': available_space,
                'is_additional': False
            }
        else:
            await update.message.reply_text("Sorry, there's no available space for that time slot. Please try another time.")
        return

    # Attempt to add the booking
    success = add_booking(user_id, booking_datetime, places)

    if success:
        await update.message.reply_text(f"Your booking for {booking_datetime.strftime('%d.%m at %H:%M')} for {places} place{'s' if places > 1 else ''} has been confirmed!")
    else:
        await update.message.reply_text("Sorry, there was an error while processing your booking. Please try again later.")

async def handle_booking_response(update, context):
    if 'pending_booking' not in context.user_data:
        await update.message.reply_text("No pending booking found. Please start a new booking.")
        return

    user_response = update.message.text.lower()
    if user_response == 'yes':
        booking_info = context.user_data['pending_booking']
        user_id = update.effective_user.id
        success = add_booking(user_id, booking_info['datetime'], booking_info['places'])

        if success:
            if booking_info.get('is_additional', False):
                await update.message.reply_text(f"Your additional booking for {booking_info['datetime'].strftime('%d.%m at %H:%M')} for {booking_info['places']} place{'s' if booking_info['places'] > 1 else ''} has been confirmed!")
            else:
                await update.message.reply_text(f"Your booking for {booking_info['datetime'].strftime('%d.%m at %H:%M')} for {booking_info['places']} place{'s' if booking_info['places'] > 1 else ''} has been confirmed!")
        else:
            await update.message.reply_text("Sorry, there was an error while processing your booking. Please try again later.")
    else:
        await update.message.reply_text("Booking cancelled. Feel free to make a new booking.")

    del context.user_data['pending_booking']