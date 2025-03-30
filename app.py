from datetime import datetime
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, CallbackContext
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from functools import wraps

from source.data_handler import (
    get_token, save_message_to_json, get_instruction_text,
    get_user_status, set_user_status)
from source.booking_handler import handle_booking_response, process_booking_request
from source.view_handler import view_bookings
from source.delete_handler import delete_bookings, setup_delete_handlers
from source.user_handler import (
    init_db, rename_user, is_user_verified, add_user, load_password,
    verify_user, require_verification)
from source.log_handler import setup_logging, get_logger
from source.change_config import (
    set_new_password, get_current_password, set_number_of_concepts,
    get_number_of_concepts, set_gym_closed_period, cancel_gym_closed_period,
    get_gym_closed_periods, is_admin)
from source.datetime_parser import parse_booking_datetime

SAVE_MESSAGES = True

# Set up logging
logger = setup_logging()
app_logger = get_logger(__name__)


'''-----------------------------------------TECHNICIAN COMMANDS-----------------------------------------'''


def rate_limit(func):
    @wraps(func)
    async def wrapped(update: Update, context: CallbackContext, *args, **kwargs):
        user_id = update.effective_user.id
        if 'last_command_time' not in context.user_data:
            context.user_data['last_command_time'] = {}

        import time
        current_time = time.time()
        context.user_data['last_command_time'][func.__name__] = current_time
        return await func(update, context, *args, **kwargs)
    return wrapped


@rate_limit
async def verify_command(update: Update, context: CallbackContext):
    """Handle the /verify command."""
    await verify_user(update, context)


def admin_only(func):
    @wraps(func)
    async def wrapped(update: Update, context: CallbackContext, *args, **kwargs):
        user_id = update.effective_user.id
        if not is_admin(user_id):
            await update.message.reply_text("Только администраторы могут использовать эту команду.")
            return
        return await func(update, context, *args, **kwargs)
    return wrapped


'''-----------------------------------------INFORMATIVE COMMANDS-----------------------------------------'''


@rate_limit
@require_verification
async def start(update: Update, context: CallbackContext):
    """Sends a welcome message with available commands and shows persistent keyboard."""
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name
    set_user_status(user_id, 'default')

    # Create a keyboard with View and Delete buttons
    keyboard = [
        [KeyboardButton("/view"), KeyboardButton("/delete")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    # Get messages from texts.json
    welcome_message = get_instruction_text(
        'start_welcome').format(user_name=user_name)
    admin_commands = get_instruction_text('start_admin_commands')
    help_message = get_instruction_text('start_help')
    not_verified_message = get_instruction_text('start_not_verified')

    full_message = welcome_message

    if is_admin(user_id):
        full_message += admin_commands
    else:
        full_message += help_message

    await update.message.reply_text(full_message, reply_markup=reply_markup, parse_mode='HTML')

    if not is_user_verified(user_id):
        await update.message.reply_text(not_verified_message)


@rate_limit
@require_verification
async def book_command(update: Update, context: CallbackContext):
    """Provides instructions for booking."""
    instruction_text = get_instruction_text()
    await update.message.reply_text(instruction_text, parse_mode='HTML')


'''-----------------------------------------USER COMMANDS-----------------------------------------'''


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


async def error_handler(update: object, context: CallbackContext) -> None:
    """Log Errors caused by Updates."""
    app_logger.warning('Update "%s" caused error "%s"', update, context.error)


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


'''-----------------------------------------ADMIN COMMANDS-----------------------------------------'''


@admin_only
@rate_limit
async def set_new_password_command(update: Update, context: CallbackContext):
    """Обработка команды /set_new_password."""
    user_id = update.effective_user.id

    if len(context.args) != 1:
        await update.message.reply_text("Пожалуйста, укажите новый пароль. Использование:\n/set_new_password <новый_пароль>")
        return

    new_password = context.args[0]
    success, message = set_new_password(user_id, new_password)

    await update.message.reply_text(message)


@rate_limit
@admin_only
async def view_current_password(update: Update, context: CallbackContext):
    """Обработка команды /view_password."""
    current_password = get_current_password()
    if current_password is not None:
        await update.message.reply_text(f"Текущий пароль для верификации: {current_password}")
    else:
        await update.message.reply_text("Не удалось получить текущий пароль.")


@rate_limit
@admin_only
async def set_number_of_concepts_command(update: Update, context: CallbackContext):
    """Обработка команды /set_number_of_concepts."""
    user_id = update.effective_user.id

    if len(context.args) != 1 or not context.args[0].isdigit():
        await update.message.reply_text("Пожалуйста, укажите корректное число. Использование: /set_number_of_concepts <число>")
        return

    new_number = int(context.args[0])
    success, message = set_number_of_concepts(user_id, new_number)

    await update.message.reply_text(message)


@rate_limit
@admin_only
async def view_number_of_concepts_command(update: Update, context: CallbackContext):
    """Обработка команды /view_number_of_concepts."""
    number_of_concepts = get_number_of_concepts()
    if number_of_concepts is not None:
        await update.message.reply_text(f"Текущее количество концептов: {number_of_concepts}")
    else:
        await update.message.reply_text("Не удалось получить количество концептов.")


@rate_limit
@admin_only
async def close_gym_command(update: Update, context: CallbackContext):
    """Обработка команды /close_GYM."""
    user_id = update.effective_user.id
    set_user_status(user_id, 'close_GYM_from')
    context.user_data['close_gym_step'] = 'start'
    await update.message.reply_text(
        "Введите дату и время (в любом из поддерживаемых форматов) с которого закрыть возможность брони.\n"
        "Например: 17.04 10:00 (закроет зал с 17го апреля с 10 утра)"
    )


@rate_limit
@admin_only
async def cancel_gym_closing_command(update: Update, context: CallbackContext):
    """Обработка команды /cancel_GYM_closing."""
    user_id = update.effective_user.id
    success, message = cancel_gym_closed_period(user_id)
    await update.message.reply_text(message)


@rate_limit
@admin_only
async def view_gym_closing_command(update: Update, context: CallbackContext):
    """Обработка команды /view_GYM_closing."""
    closed_from, closed_until = get_gym_closed_periods()
    if closed_from != "NaN" and closed_until != "NaN":
        await update.message.reply_text(f"Зал закрыт с {closed_from} до {closed_until}.")
    else:
        await update.message.reply_text("В настоящее время нет запланированного закрытия зала.")


"""-----------------------------------------CALLBACKS-----------------------------------------"""


async def handle_message(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    user_status = get_user_status(user_id)

    if user_status == 'default':
        if is_user_verified(user_id):
            await handle_booking_message(update, context)
        else:
            set_user_status(user_id, 'verification_pass')
            await update.message.reply_text("Неверный пароль. пожалуйста, введите пароль для верификации:")
    elif user_status == 'wait_book_response':
        await handle_booking_response(update, context)
    elif user_status == 'verification_pass':
        if update.message.text == load_password():
            set_user_status(user_id, 'verification_name')
            await update.message.reply_text("Пароль верифицирован. Введите ваше имя:")
        else:
            await update.message.reply_text("Неверный пароль. пожалуйста, введите пароль для верификации:")
    elif user_status == 'verification_name':
        name = update.message.text
        telegram_link = f"https://t.me/{update.effective_user.username}" if update.effective_user.username else ""
        add_user(user_id, name, telegram_link)
        set_user_status(user_id, 'default')
        await update.message.reply_text("Верификация пройдена. Вы можете пользоваться ботом.\nСоветую начать с \start")
    elif user_status == 'close_GYM_from':
        start_datetime, _, _ = parse_booking_datetime(update.message.text)
        if start_datetime is None:
            await update.message.reply_text("Неверный формат даты и времени. Пожалуйста, попробуйте снова.")
        else:
            context.user_data['close_gym_start'] = start_datetime
            set_user_status(user_id, 'close_GYM_till')
            await update.message.reply_text("Введите дату и время до которого закрыть возможность брони.")
    elif user_status == 'close_GYM_till':
        end_datetime, _, _ = parse_booking_datetime(update.message.text)
        if end_datetime is None:
            await update.message.reply_text("Неверный формат даты и времени. Пожалуйста, попробуйте снова.")
        else:
            start_datetime = context.user_data['close_gym_start']
            success, message = set_gym_closed_period(
                user_id, start_datetime, end_datetime)
            if success:
                await update.message.reply_text(f"Зал закрыт с {start_datetime.strftime('%d.%m.%Y %H:%M')} до {end_datetime.strftime('%d.%m.%Y %H:%M')}.")
            else:
                await update.message.reply_text(f"Ошибка при закрытии зала: {message}")
            set_user_status(user_id, 'default')
            del context.user_data['close_gym_start']
    else:
        await update.message.reply_text("Unexpected state. Please use /start to reset.")


async def button_callback(update: Update, context: CallbackContext):
    """Handle button callbacks."""
    query = update.callback_query
    await query.answer()

    if query.data == "view":
        # Create a new update object with the original message but modified text
        new_update = Update(
            update.update_id, message=update.callback_query.message)
        new_update.message.text = "/view"
        new_update.message.from_user = update.callback_query.from_user
        await view_bookings(new_update, context)
    elif query.data == "delete":
        # Create a new update object with the original message but modified text
        new_update = Update(
            update.update_id, message=update.callback_query.message)
        new_update.message.text = "/delete"
        new_update.message.from_user = update.callback_query.from_user
        await delete_bookings(new_update, context)
    # Remove any handling of "delete_" prefixed callbacks here, as they're handled by delete_booking_callback


async def log_message(update: Update, context: CallbackContext) -> None:
    """Log the user's message with timestamp and optionally save to JSON."""
    user = update.effective_user
    message = update.message
    timestamp = datetime.now()

    # Log to console/file
    app_logger.info(
        f"[{timestamp.strftime('%Y-%m-%d %H:%M:%S')}] User {user.id} ({user.username}) sent: '{message.text}'")

    # Save to JSON if the flag is set
    if SAVE_MESSAGES:
        save_message_to_json(user.id, user.username, message.text, timestamp)


def main() -> None:
    app_logger.info("Starting bot application")
    init_db()

    TOKEN = get_token()
    application = Application.builder().token(TOKEN).build()

    # Command handlers
    command_handlers = [
        ("start", start),
        ("help", start),
        ("verify", verify_command),
        ("book", book_command),
        ("delete", delete_command),
        ("view", view_bookings),
        ("my", view_bookings),
        ("rename", rename_command),
        ("buttons", show_buttons),
    ]

    for command, handler in command_handlers:
        application.add_handler(CommandHandler(command, handler))

    # Admin-only command handlers
    admin_command_handlers = [
        ("set_new_password", set_new_password_command),
        ("view_password", view_current_password),
        ("set_number_of_concepts", set_number_of_concepts_command),
        ("view_number_of_concepts", view_number_of_concepts_command),
        ("close_GYM", close_gym_command),
        ("cancel_GYM_closing", cancel_gym_closing_command),
        ("view_GYM_closing", view_gym_closing_command),
    ]

    for command, handler in admin_command_handlers:
        application.add_handler(CommandHandler(command, handler))

    # Set up delete handlers first (to handle delete_ callbacks)
    setup_delete_handlers(application)

    # Add callback query handler for view and delete buttons (but not delete_ callbacks)
    application.add_handler(CallbackQueryHandler(
        button_callback, pattern='^(?!delete_).*$'))

    # Add message handler for all text messages
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        handle_message
    ))

    # Add error handler
    application.add_error_handler(error_handler)

    # Add message logging
    application.add_handler(MessageHandler(
        filters.TEXT, log_message), group=42)

    app_logger.info("Bot handlers configured, starting polling")
    # Start the Bot
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
