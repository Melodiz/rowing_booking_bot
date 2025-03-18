import logging
from datetime import datetime, time, timedelta
from .data_handler import load_bookings, get_available_places, get_user_bookings, add_booking, get_user_name, get_all_bookings
from .datetime_parser import parse_booking_datetime
from .user_handler import is_user_verified
from telegram.ext import CallbackContext
from telegram import Update
from source.log_handler import get_logger

logger = get_logger(__name__)
MAX_BOOKINGS_PER_HOUR = 6

async def process_booking_request(update: Update, context: CallbackContext):
    """Process a booking request."""
    user_id = update.effective_user.id
    
    # Check if the user is verified
    if not is_user_verified(user_id):
        await update.message.reply_text(
            "Вам необходимо пройти верификацию. Используйте команду /verify."
            )
        return

    message_text = update.message.text
    
    try:
        parsed_result = parse_booking_datetime(message_text)
        if isinstance(parsed_result, tuple) and len(parsed_result) == 3:
            booking_datetime, places, duration = parsed_result
        else:
            raise ValueError("Ошибка парсинг даты и времени.")
    except Exception as e:
        logger.error(f"Error parsing booking datetime: {e}")
        await update.message.reply_text(
            "Неподдерживаймый формат записи. Пожалуйста воспользуйтесь командой /book"
            )
        return
    
    
    if places <= 0:
        await update.message.reply_text(
            "Хахахаха, забавно, но мой автор уже подумал об этом)\n"
            "Введите пожалуйста положительное число концептов")
        return
    
    if booking_datetime <= datetime.now():
        await update.message.reply_text("К сожалению это время уже прошло. Пожалуйста, выберите другое время.")
        return
    # Check if the booking time is valid
    is_valid, error_message = is_valid_booking_time(booking_datetime, duration)
    if not is_valid:
        await update.message.reply_text(error_message)
        return
    # Load the latest booking data
    load_bookings()
    
    # Check available space
    available_space = get_available_places(booking_datetime)
    
    if available_space >= places:
        # Attempt to add the booking
        success = add_booking(user_id, booking_datetime, places, duration)
        if success:
            duration_text = f" на {duration} минут" if duration != 60 else ""
            await update.message.reply_text(f"Ваше бронирование на {booking_datetime.strftime('%d.%m в %H:%M')}{duration_text} на {places} концепт{'' if places == 1 else 'а' if places < 5 else 'ов'} подтверждено!")
        else:
            await update.message.reply_text("Извините, произошла ошибка при обработке вашего бронирования. Пожалуйста, попробуйте позже.")
    else:
        if available_space > 0:
            duration_text = f" на {duration} минут" if duration != 60 else ""
            await update.message.reply_text(f"Извините, на это время доступно только {available_space} концепт{'' if available_space == 1 else 'а' if available_space < 5 else 'ов'}{duration_text}. Хотите забронировать доступные места? (Yes/No)")
            context.user_data['pending_booking'] = {
                'datetime': booking_datetime,
                'places': available_space,
                'duration': duration
            }
        else:
            await update.message.reply_text("Извините, на это время нет свободных мест. Пожалуйста, выберите другое время.")
def is_valid_booking_time(booking_datetime, duration=60):
    """Check if the booking time is within the allowed time slots."""
    day_of_week = booking_datetime.weekday()
    booking_time_start = booking_datetime.time()
    booking_datetime_end = booking_datetime + timedelta(minutes=duration)
    booking_time_end = booking_datetime_end.time()

    if day_of_week == 6:  # Sunday (0 is Monday, 6 is Sunday)
        return False, "Извините, в воскресенье зал на Малой Ордынке 29 не работает."
    
    if day_of_week == 5:  # Saturday
        if time(8, 0) <= booking_time_start and booking_time_end <= time(20, 0):
            return True, ""
        else:
            return False, "По субботам бронирование доступно только с 8:00 до 19:00. Зал на МО29 20:00"
    
    else:  # Monday to Friday
        if time(8, 0) <= booking_time_start and booking_time_end <= time(21, 0):
            return True, ""
        else:
            return False, "В будние дни бронирование доступно только с 8:00 до 20:00. Зал на МО29 до 21:00"

async def handle_booking_response(update, context):
    if 'pending_booking' not in context.user_data:
        await update.message.reply_text("Нет ожидающего бронирования. Пожалуйста, начните новое бронирование.")
        return

    user_response = update.message.text.lower()
    if user_response == 'yes':
        booking_info = context.user_data['pending_booking']
        user_id = update.effective_user.id
        success = add_booking(user_id, booking_info['datetime'], booking_info['places'])

        if success:
            booking_time = booking_info['datetime'].strftime('%d.%m в %H:%M')
            duration_text = f" на {booking_info.get('duration', 60)} минут" if booking_info.get('duration', 60) != 60 else ""
            places = booking_info['places']
            places_text = f"{places} концепт{'' if places == 1 else 'а' if places < 5 else 'ов'}"
            if booking_info.get('is_additional', False):
                await update.message.reply_text(f"Ваше дополнительное бронирование на {booking_time}{duration_text} на {places_text} подтверждено!")
            else:
                await update.message.reply_text(f"Ваше бронирование на {booking_time}{duration_text} на {places_text} подтверждено!")
        else:
            await update.message.reply_text("Извините, произошла ошибка при обработке вашего бронирования. Пожалуйста, попробуйте позже.")
    else:
        await update.message.reply_text("Бронирование отменено. Вы можете сделать новое бронирование.")

    del context.user_data['pending_booking']
