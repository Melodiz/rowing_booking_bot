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
        await update.message.reply_text(
            "Вам необходимо пройти верификацию. Используйте команду /verify."
            )
        return

    message_text = update.message.text
    
    try:
        parsed_result = parse_booking_datetime(message_text)
        if isinstance(parsed_result, tuple) and len(parsed_result) == 2:
            booking_datetime, places = parsed_result
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
        success = add_booking(user_id, booking_datetime, places)
        if success:
            await update.message.reply_text(f"Ваше бронирование на {booking_datetime.strftime('%d.%m в %H:%M')} на {places} концепт{'' if places == 1 else 'а' if places < 5 else 'ов'} подтверждено!")
        else:
            await update.message.reply_text("Извините, произошла ошибка при обработке вашего бронирования. Пожалуйста, попробуйте позже.")
    else:
        if available_space > 0:
            await update.message.reply_text(f"Извините, на это время доступно только {available_space} концепт{'' if available_space == 1 else 'а' if available_space < 5 else 'ов'}. Хотите забронировать доступные места? (Yes/No)")
            context.user_data['pending_booking'] = {
                'datetime': booking_datetime,
                'places': available_space
            }
        else:
            await update.message.reply_text("Извините, на это время нет свободных мест. Пожалуйста, выберите другое время.")

def is_valid_booking_time(booking_datetime):
    """Check if the booking time is within the allowed time slots."""
    day_of_week = booking_datetime.weekday()
    booking_time = booking_datetime.time()

    if day_of_week == 6:  # Sunday (0 is Monday, 6 is Sunday)
        return False, "Извините, в воскресенье зал на Малой Ордынке 29 не работает."
    
    if day_of_week == 5:  # Saturday
        if time(8, 0) <= booking_time < time(20, 0):
            return True, ""
        else:
            return False, "По субботам бронирование доступно только с 8:00 до 19:00. Зал на МО29 20:00"
    
    else:  # Monday to Friday
        if time(8, 0) <= booking_time < time(21, 0):
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
            if booking_info.get('is_additional', False):
                await update.message.reply_text(f"Ваше дополнительное бронирование на {booking_info['datetime'].strftime('%d.%m в %H:%M')} на {booking_info['places']} концепт{'' if booking_info['places'] == 1 else 'а' if booking_info['places'] < 5 else 'ов'} подтверждено!")
            else:
                await update.message.reply_text(f"Ваше бронирование на {booking_info['datetime'].strftime('%d.%m в %H:%M')} на {booking_info['places']} концепт{'' if booking_info['places'] == 1 else 'а' if booking_info['places'] < 5 else 'ов'} подтверждено!")
        else:
            await update.message.reply_text("Извините, произошла ошибка при обработке вашего бронирования. Пожалуйста, попробуйте позже.")
    else:
        await update.message.reply_text("Бронирование отменено. Вы можете сделать новое бронирование.")

    del context.user_data['pending_booking']
