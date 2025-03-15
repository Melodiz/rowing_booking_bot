import logging
import asyncio
from datetime import datetime
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler
from source.data_handler import get_token, load_bookings, save_message_to_json, get_user_bookings
from source.booking_handler import handle_booking_response, process_booking_request
from source.view_handler import view_bookings, format_bookings
from source.delete_handler import delete_bookings, setup_delete_handlers
from telegram.ext import CallbackContext, CommandHandler, MessageHandler, filters, Application
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from functools import wraps
from source.user_handler import *
import re


SAVE_MESSAGES = True 

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

logger = logging.getLogger(__name__)

TOKEN = get_token()

# Rate limiting
def rate_limit(func):
    @wraps(func)
    async def wrapped(update: Update, context: CallbackContext, *args, **kwargs):
        user_id = update.effective_user.id
        if 'last_command_time' not in context.user_data:
            context.user_data['last_command_time'] = {}
        
        import time
        current_time = time.time()
        if func.__name__ in context.user_data['last_command_time']:
            last_time = context.user_data['last_command_time'][func.__name__]
            # if current_time - last_time < 0.1:  
            #     await update.message.reply_text("Please wait a moment before using this command again.")
            #     return
        
        context.user_data['last_command_time'][func.__name__] = current_time
        return await func(update, context, *args, **kwargs)
    return wrapped

@rate_limit
async def verify_command(update: Update, context: CallbackContext):
    """Handle the /verify command."""
    await verify_user(update, context)

@rate_limit
@require_verification
async def start(update: Update, context: CallbackContext):
    """Sends a welcome message with available commands and shows persistent keyboard."""
    # Create a keyboard with only View and Delete buttons
    keyboard = [
        [KeyboardButton("/view"), KeyboardButton("/delete")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        'Добро пожаловать! Вот доступные команды:\n\n'
        '/view - Посмотреть брони всех пользователей\n'
        '/delete - Отменить свои брони\n'
        '/my - Посмотреть свои брони\n'
        '/book - Инструкция по брони концептов\n'
        '/verify - Подтвердить аккаунт\n'
        '/rename - задать новое имя пользователя\n',
        reply_markup=reply_markup
    )

@rate_limit
@require_verification
@rate_limit
@require_verification
async def book_command(update: Update, context: CallbackContext):
    """Provides instructions for booking."""
    await update.message.reply_text(
        'Чтобы забронировать концепт, отправьте сообщение в следующем формате:\n\n'
        '<b>[дата] [время] [количество] [длительность]</b>\n\n'
        '<b>Параметры:</b>\n'
        '• <b>дата</b> - день бронирования (необязательно, по умолчанию сегодня)\n'
        '• <b>время</b> - время начала бронирования (обязательно)\n'
        '• <b>количество</b> - число концептов (необязательно, по умолчанию 1)\n'
        '• <b>длительность</b> - в минутах (необязательно, по умолчанию 60)\n\n'
        '<b>Примеры:</b>\n'
        '• <code>24.03 10:00 2 90</code> - 24 марта в 10:00, 2 концепта на 90 минут\n'
        '• <code>10.03 15:00 2</code> - 10 марта в 15:00, 2 концепта на 60 минут\n'
        '• <code>10.03 15:00</code> - 10 марта в 15:00, 1 концепт на 60 минут\n'
        '• <code>15:00</code> - сегодня в 15:00, 1 концепт на 60 минут\n\n'
        '<b>Форматы даты:</b>\n'
        '• <code>дд.мм</code> (например, 10.03)\n'
        '• <code>дд/мм</code> (например, 10/03)\n'
        '• <code>дд</code> (например, 10 - текущий или следующий месяц)\n\n'
        '<b>Форматы времени:</b>\n'
        '• <code>чч:мм</code> (например, 15:30)\n'
        '• <code>чч.мм</code> (например, 15.30)\n'
        '• <code>ччмм</code> (например, 1530)\n\n'
        'Система автоматически проверит наличие свободных мест и расписание зала.',
        parse_mode='HTML'
    )
@rate_limit
@require_verification
async def rename_command(update: Update, context: CallbackContext):
    """Handle the /rename command."""
    user_id = update.effective_user.id
    
    if len(context.args) == 0:
        await update.message.reply_text("Пожалуйста, укажите ваше новое имя после команды /rename. Например: /rename Иванов")
        return
    
    new_name = ' '.join(context.args)
    
    if rename_user(user_id, new_name):
        await update.message.reply_text(f"Ваше имя было обновлено на: {new_name}")
    else:
        await update.message.reply_text(
            "Произошла ошибка при обновлении вашего имени. Пожалуйста, попробуйте позже.\n"
            "Если проблема не пройдет, пожалуйста, напиши моему автору: @Mellodizzz")

@rate_limit
@require_verification
async def delete_command(update: Update, context: CallbackContext):
    """Handle the /delete command."""
    await delete_bookings(update, context)

@rate_limit
@require_verification
async def my_bookings(update: Update, context: CallbackContext):
    """Handle the /my command to show user's bookings."""
    user_id = update.effective_user.id

    user_bookings = get_user_bookings(user_id)
    
    if not user_bookings:
        await update.message.reply_text("У вас нет актуальных броней.")
        return

    formatted_bookings = format_bookings(user_bookings)
    await update.message.reply_text(f"Ваши бронирования:\n{formatted_bookings}")

async def error_handler(update: object, context: CallbackContext) -> None:
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, context.error)


@rate_limit
@require_verification
async def toggle_message_saving(update: Update, context: CallbackContext):
    """Toggle message saving on or off."""
    global SAVE_MESSAGES
    SAVE_MESSAGES = not SAVE_MESSAGES
    status = "включено" if SAVE_MESSAGES else "отключено"
    await update.message.reply_text(f"Сохранение сообщений теперь {status}.")

@rate_limit
@require_verification
async def handle_booking_message(update: Update, context: CallbackContext):
    """Handle booking messages."""
    await process_booking_request(update, context)


@rate_limit
@require_verification
async def show_buttons(update: Update, context: CallbackContext):
    """Show buttons for view and delete commands as persistent keyboard."""
    keyboard = [
        [KeyboardButton("/view"), KeyboardButton("/delete")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text('Выберите действие:', reply_markup=reply_markup)

    
async def button_callback(update: Update, context: CallbackContext):
    """Handle button callbacks."""
    query = update.callback_query
    await query.answer()
    
    if query.data == "view":
        # Create a new update object with the original message but modified text
        new_update = Update(update.update_id, message=update.callback_query.message)
        new_update.message.text = "/view"
        new_update.message.from_user = update.callback_query.from_user
        await view_bookings(new_update, context)
    elif query.data == "delete":
        # Create a new update object with the original message but modified text
        new_update = Update(update.update_id, message=update.callback_query.message)
        new_update.message.text = "/delete"
        new_update.message.from_user = update.callback_query.from_user
        await delete_bookings(new_update, context)
    # Remove any handling of "delete_" prefixed callbacks here, as they're handled by delete_booking_callback

async def handle_message(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if is_user_verified(user_id):
        # Updated regex pattern to match all supported booking formats with optional duration
        booking_pattern = r'^(\d{1,2}([./])\d{1,2}(\2|\s)\d{2}[:.]?\d{2}|\d{1,2}\s\d{2}[:.]?\d{2}|\d{4}|\d{1,2}[:]\d{2}|\d{1,2}[.]\d{2})(\s+\d+)(\s+\d+)?$'        
        if re.match(booking_pattern, update.message.text):
            await handle_booking_message(update, context)
        else:
            await update.message.reply_text("Извините, я не понял эту команду. Используйте /help, чтобы увидеть доступные команды.")
    else:
        await handle_verification(update, context)

async def log_message(update: Update, context: CallbackContext) -> None:
    """Log the user's message with timestamp and optionally save to JSON."""
    user = update.effective_user
    message = update.message
    timestamp = datetime.now()

    # Log to console/file
    logger.info(f"[{timestamp.strftime('%Y-%m-%d %H:%M:%S')}] User {user.id} ({user.username}) sent: '{message.text}'")

    # Save to JSON if the flag is set
    if SAVE_MESSAGES:
        save_message_to_json(user.id, user.username, message.text, timestamp)

def main() -> None:
    init_db()

    application = Application.builder().token(TOKEN).build()

    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", start))
    application.add_handler(CommandHandler("verify", verify_command))
    application.add_handler(CommandHandler("book", book_command))
    application.add_handler(CommandHandler("delete", delete_command))
    application.add_handler(CommandHandler("view", view_bookings))
    application.add_handler(CommandHandler("my", view_bookings))
    application.add_handler(CommandHandler("rename", rename_command))
    application.add_handler(CommandHandler("buttons", show_buttons))  # Add the new command

    # Set up delete handlers first (to handle delete_ callbacks)
    setup_delete_handlers(application)

    # Add callback query handler for view and delete buttons (but not delete_ callbacks)
    application.add_handler(CallbackQueryHandler(button_callback, pattern='^(?!delete_).*$'))

    # Add handler for booking response
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'^(yes|no|Yes|No|NO)$'), handle_booking_response))

    # Add message handlers
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Add error handler
    application.add_error_handler(error_handler)

    # Add message logging
    application.add_handler(MessageHandler(filters.TEXT, log_message), group=42)

    # Start the Bot
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()