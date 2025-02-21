from datetime import datetime
from .data_handler import *
from .datetime_parser import parse_booking_datetime
async def book_table(update, context):
    message_text = update.message.text
    user_id = update.effective_user.id
    
    # Load the latest booking data
    load_bookings()
    
    booking_datetime, places = parse_booking_datetime(message_text)
    
    if booking_datetime is None:
        await update.message.reply_text("Invalid format. Please use one of these formats:\n"
                                        # ... (keep the existing format instructions)
                                        "For example: 25.06 19:30 or 25/06 19:30 3 or 25 19:30 2 or 25 19.30 or 25 1930 4")
        return
    
    if booking_datetime <= datetime.now():
        await update.message.reply_text("Sorry, you can't book for a past date and time.")
        return
    
    # Check available space
    available_space = get_available_places(booking_datetime)
    
    # Check if the user already has a booking for this date-time
    user_bookings = get_user_bookings(user_id)
    existing_booking = next((b for b in user_bookings if b['date'] == booking_datetime.date() and b['time'] == booking_datetime.time()), None)
    
    if existing_booking:
        if available_space < places:
            if available_space > 0:
                await update.message.reply_text(f"You already have a booking for this time, and there are only {available_space} additional place(s) available. Would you like to book the available places? (Yes/No)")
                context.user_data['pending_booking'] = {
                    'datetime': booking_datetime,
                    'places': available_space,
                    'is_additional': True
                }
            else:
                await update.message.reply_text("Sorry, there's no available space for additional bookings at that time slot. Please try another time.")
            return
        else:
            context.user_data['pending_booking'] = {
                'datetime': booking_datetime,
                'places': places,
                'is_additional': True
            }
            await update.message.reply_text(f"You already have a booking for {booking_datetime.strftime('%d.%m at %H:%M')}. Are you sure you want to make an additional booking for {places} place(s)? (Yes/No)")
            return
    
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
    success = True
    for _ in range(places):
        if not add_booking(user_id, booking_datetime):
            success = False
            break

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
        success = True
        for _ in range(booking_info['places']):
            if not add_booking(user_id, booking_info['datetime']):
                success = False
                break

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