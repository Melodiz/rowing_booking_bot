import json
import logging
import pandas as pd
from datetime import datetime, timedelta
import os

# File to store bookings
BOOKINGS_FILE = 'bookings.json'

# Initialize DataFrame to store bookings
bookings_df = pd.DataFrame(columns=['user_id', 'date', 'time'])

# Maximum number of bookings per hour
MAX_BOOKINGS_PER_HOUR = 6


def get_token():
    try:
        with open('token.json', 'r') as file:
            data = json.load(file)
            return data['bot_token']
    except FileNotFoundError:
        logging.error("token.json file not found")
        return None
    except json.JSONDecodeError:
        logging.error("Error decoding JSON from token.json")
        return None
    except KeyError:
        logging.error("'bot_token' key not found in token.json")
        return None


def load_bookings():
    remove_old_bookings()
    global bookings_df
    try:
        with open(BOOKINGS_FILE, 'r') as file:
            bookings_data = json.load(file)
            bookings_df = pd.DataFrame(bookings_data)
            bookings_df['date'] = pd.to_datetime(bookings_df['date']).dt.date
            bookings_df['time'] = pd.to_datetime(
                bookings_df['time'], format='%H:%M:%S').dt.time
    except FileNotFoundError:
        logging.info(
            "Bookings file not found. Starting with an empty DataFrame.")
    except json.JSONDecodeError:
        logging.error(
            "Error decoding JSON from bookings file. Starting with an empty DataFrame.")


def save_bookings(bookings):
    # Convert datetime objects to string for JSON serialization
    serializable_bookings = []
    for booking in bookings:
        serializable_booking = booking.copy()
        serializable_booking['date'] = booking['date'].strftime('%Y-%m-%d')
        serializable_booking['time'] = booking['time'].strftime('%H:%M:%S')
        serializable_bookings.append(serializable_booking)

    # Save the bookings to a JSON file
    with open('bookings.json', 'w') as f:
        json.dump(serializable_bookings, f, indent=2)


def add_booking(user_id, booking_datetime):
    global bookings_df
    new_booking = pd.DataFrame({
        'user_id': [user_id],
        'date': [booking_datetime.date()],
        'time': [booking_datetime.time()]
    })
    bookings_df = pd.concat([bookings_df, new_booking], ignore_index=True)
    save_bookings()


def is_space_available(booking_datetime):
    global bookings_df
    start_time = booking_datetime.replace(minute=0, second=0, microsecond=0)
    end_time = start_time + timedelta(hours=1)
    
    existing_bookings = bookings_df[
        (bookings_df['date'] == booking_datetime.date()) &
        (bookings_df['time'] >= start_time.time()) &
        (bookings_df['time'] < end_time.time())
    ]
    
    return len(existing_bookings) < MAX_BOOKINGS_PER_HOUR

def get_available_places(booking_datetime):
    remove_old_bookings()
    global bookings_df
    start_time = booking_datetime.replace(minute=0, second=0, microsecond=0)
    end_time = start_time + timedelta(hours=1)
    
    existing_bookings = bookings_df[
        (bookings_df['date'] == booking_datetime.date()) &
        (bookings_df['time'] >= start_time.time()) &
        (bookings_df['time'] < end_time.time())
    ]
    
    occupied_places = len(existing_bookings)
    available_places = MAX_BOOKINGS_PER_HOUR - occupied_places
    
    return max(0, available_places)  # Ensure we don't return a negative number

def add_booking(user_id, booking_datetime):
    bookings = get_all_bookings()
    new_booking = {
        'user_id': user_id,
        'date': booking_datetime.date(),
        'time': booking_datetime.time()
    }
    bookings.append(new_booking)
    save_bookings(bookings)
    return True  # You might want to add some validation logic here

def get_all_bookings():
    try:
        with open('bookings.json', 'r') as f:
            bookings = json.load(f)
        
        # Convert string dates and times back to datetime objects
        for booking in bookings:
            booking['date'] = datetime.strptime(booking['date'], '%Y-%m-%d').date()
            booking['time'] = datetime.strptime(booking['time'], '%H:%M:%S').time()
        
        return bookings
    except FileNotFoundError:
        return []  # Return an empty list if the file doesn't exist yet


def save_message_to_json(user_id, username, message_text, timestamp):
    """Save a message to a JSON file."""
    log_dir = "message_logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    filename = f"{log_dir}/message_{timestamp.strftime('%Y%m%d_%H%M%S')}_{user_id}.json"
    
    message_data = {
        "user_id": user_id,
        "username": username,
        "message": message_text,
        "timestamp": timestamp.isoformat()
    }
    
    with open(filename, 'w') as f:
        json.dump(message_data, f, indent=2)

def get_user_bookings(user_id):
    """
    Retrieve all bookings for a specific user.
    """
    remove_old_bookings()
    all_bookings = get_all_bookings()
    user_bookings = [booking for booking in all_bookings if booking['user_id'] == user_id]
    return user_bookings

def remove_old_bookings():
    bookings = get_all_bookings()
    current_datetime = datetime.now()
    updated_bookings = [
        booking for booking in bookings
        if datetime.combine(booking['date'], booking['time']) > current_datetime
    ]
    save_bookings(updated_bookings)
    return updated_bookings