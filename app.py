import logging
import asyncio
from datetime import datetime
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from source.data_handler import get_token, load_bookings, save_message_to_json, get_user_bookings
from source.booking_handler import book_table, handle_booking_response
from source.view_handler import view_bookings, format_bookings
from source.delete_handler import delete_bookings, setup_delete_handlers
from telegram.ext import CallbackContext, CommandHandler, MessageHandler, filters, Application
from telegram import Update
from functools import wraps

SAVE_MESSAGES = False 

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
            if current_time - last_time < 3:  # 3 seconds cooldown
                await update.message.reply_text("Please wait a moment before using this command again.")
                return
        
        context.user_data['last_command_time'][func.__name__] = current_time
        return await func(update, context, *args, **kwargs)
    return wrapped

@rate_limit
async def start(update: Update, context: CallbackContext):
    """Sends a welcome message with available commands."""
    await update.message.reply_text(
        'Welcome! Here are the available commands:\n\n'
        '/book - Book a concept\n'
        '/view - View all booked concepts\n'
        '/view dd.mm - View bookings for a specific day\n'
        '/my - View your bookings\n'
        '/delete - Delete your bookings'
    )

@rate_limit
async def book_command(update: Update, context: CallbackContext):
    """Provides instructions for booking."""
    await update.message.reply_text(
        'To book a concept, simply send your booking request in one of these formats:\n\n'
        'dd.mm hh:mm [number_of_places]\n'
        'dd.mm hh.mm [number_of_places]\n'
        'dd.mm hhmm [number_of_places]\n'
        'dd/mm hh:mm [number_of_places]\n'
        'dd/mm hh.mm [number_of_places]\n'
        'dd/mm hhmm [number_of_places]\n\n'
        'For example:\n'
        '25.06 19:30\n'
        '25/06 19:30 2\n'
        '25 1930 3\n\n'
        'The number of places is optional. If not specified, it defaults to 1.\n'
        'Just send your booking request in one of these formats, and I\'ll process it for you!'
    )

@rate_limit
async def delete_command(update: Update, context: CallbackContext):
    """Handle the /delete command."""
    await delete_bookings(update, context)

@rate_limit
async def my_bookings(update: Update, context: CallbackContext):
    """Handle the /my command to show user's bookings."""
    user_id = update.effective_user.id

    user_bookings = get_user_bookings(user_id)
    
    if not user_bookings:
        await update.message.reply_text("You don't have any bookings.")
        return

    formatted_bookings = format_bookings(user_bookings)
    await update.message.reply_text(f"Your bookings:\n{formatted_bookings}")

async def error_handler(update: object, context: CallbackContext) -> None:
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, context.error)

@rate_limit
async def toggle_message_saving(update: Update, context: CallbackContext):
    """Toggle message saving on or off."""
    global SAVE_MESSAGES
    SAVE_MESSAGES = not SAVE_MESSAGES
    status = "enabled" if SAVE_MESSAGES else "disabled"
    await update.message.reply_text(f"Message saving is now {status}.")

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
    application = Application.builder().token(TOKEN).build()

    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("book", book_command))
    application.add_handler(CommandHandler("delete", delete_command))
    # application.add_handler(CommandHandler("toggle_save", toggle_message_saving))
    application.add_handler(CommandHandler("view", view_bookings))
    application.add_handler(CommandHandler("my", my_bookings))

    # Add handler for booking response
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'^(yes|no)$'), handle_booking_response))

    # Add message handlers
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, book_table))

    # Add error handler
    application.add_error_handler(error_handler)

    # Add message logging
    application.add_handler(MessageHandler(filters.TEXT, log_message), group=42)

    # Set up delete handlers
    setup_delete_handlers(application)

    # Start the Bot
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()