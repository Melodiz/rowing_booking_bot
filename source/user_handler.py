import pandas as pd
from telegram import Update
from telegram.ext import CallbackContext
import os

# File to store the user data
USER_DB_FILE = 'users.csv'

# Initialize the database
def init_db():
    if not os.path.exists(USER_DB_FILE):
        df = pd.DataFrame(columns=['user_id', 'name', 'telegram_link'])
        df.to_csv(USER_DB_FILE, index=False)

def rename_user(user_id, new_name):
    df = pd.read_csv('users.csv')
    if user_id in df['user_id'].values:
        df.loc[df['user_id'] == user_id, 'name'] = new_name
        df.to_csv('users.csv', index=False)
        return True
    return False

def is_user_verified(user_id):
    try:
        df = pd.read_csv(USER_DB_FILE)
        return user_id in df['user_id'].values
    except FileNotFoundError:
        return False

# Add a new user to the database
def add_user(user_id, name, telegram_link):
    df = pd.read_csv(USER_DB_FILE)
    new_user = pd.DataFrame({'user_id': [user_id], 'name': [name], 'telegram_link': [telegram_link]})
    df = pd.concat([df, new_user], ignore_index=True)
    df.to_csv(USER_DB_FILE, index=False)

def load_password():
    with open('password.txt', 'r') as f:
        return f.read().strip()

# Verification process
async def verify_user(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if is_user_verified(user_id):
        await update.message.reply_text("You are already verified.")
        return

    if 'verification_step' not in context.user_data:
        context.user_data['verification_step'] = 'password'
        await update.message.reply_text("Please enter the verification password:")
    elif context.user_data['verification_step'] == 'password':
        if update.message.text == load_password():
            context.user_data['verification_step'] = 'name'
            await update.message.reply_text("Password correct. Please enter your name:")
        else:
            await update.message.reply_text("Incorrect password. Please try again.")
    elif context.user_data['verification_step'] == 'name':
        name = update.message.text
        telegram_link = f"https://t.me/{update.effective_user.username}" if update.effective_user.username else ""
        add_user(user_id, name, telegram_link)
        del context.user_data['verification_step']
        await update.message.reply_text("Verification complete. You can now use the bot.")

# New function to handle verification process
async def handle_verification(update: Update, context: CallbackContext):
    if 'verification_step' in context.user_data:
        await verify_user(update, context)
    else:
        await update.message.reply_text("You need to start the verification process. Please use /verify command.")

# Decorator to check if user is verified
def require_verification(func):
    async def wrapper(update: Update, context: CallbackContext, *args, **kwargs):
        user_id = update.effective_user.id
        if is_user_verified(user_id):
            return await func(update, context, *args, **kwargs)
        elif 'verification_step' in context.user_data:
            await handle_verification(update, context)
        else:
            await update.message.reply_text("You need to be verified to use this command. Please use /verify to start the verification process.")
    return wrapper