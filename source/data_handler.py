import pandas as pd
import json
import logging
from datetime import datetime, timedelta, date, time
import os

BOOKINGS_FILE = 'bookings.json'
bookings_df = pd.DataFrame(columns=['user_id', 'date', 'time', 'places'])

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
    global bookings_df
    try:
        with open(BOOKINGS_FILE, 'r') as file:
            bookings_data = json.load(file)
            if bookings_data:
                bookings_df = pd.DataFrame(bookings_data)
                bookings_df['date'] = pd.to_datetime(bookings_df['date']).dt.date
                bookings_df['time'] = pd.to_datetime(bookings_df['time'], format='%H:%M:%S').dt.time
            else:
                bookings_df = pd.DataFrame(columns=['user_id', 'date', 'time', 'places'])
    except FileNotFoundError:
        logging.info("Bookings file not found. Starting with an empty DataFrame.")
        bookings_df = pd.DataFrame(columns=['user_id', 'date', 'time', 'places'])
    except json.JSONDecodeError:
        logging.error("Error decoding JSON from bookings file. Starting with an empty DataFrame.")
        bookings_df = pd.DataFrame(columns=['user_id', 'date', 'time', 'places'])


def save_bookings(updated_bookings=None):
    global bookings_df
    if updated_bookings is not None:
        bookings_df = pd.DataFrame(updated_bookings)
    
    # Convert date and time objects to strings
    bookings_data = bookings_df.to_dict('records')
    for booking in bookings_data:
        if isinstance(booking['date'], date):
            booking['date'] = booking['date'].isoformat()
        if isinstance(booking['time'], time):
            booking['time'] = booking['time'].isoformat()
    
    with open(BOOKINGS_FILE, 'w') as file:
        json.dump(bookings_data, file, default=str)


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
    available_places = get_available_places(booking_datetime)
    return available_places > 0


def get_available_places(booking_datetime):
    remove_old_bookings()
    global bookings_df
    if bookings_df.empty:
        return MAX_BOOKINGS_PER_HOUR

    # Convert date strings to datetime objects
    bookings_df['start_datetime'] = pd.to_datetime(bookings_df['date'].astype(str) + ' ' + bookings_df['time'].astype(str))
    bookings_df['end_datetime'] = bookings_df['start_datetime'] + timedelta(hours=1)

    # Define the booking time range
    booking_start = booking_datetime
    booking_end = booking_start + timedelta(hours=1)

    # Calculate intersecting bookings
    intersecting_bookings = bookings_df[
        (bookings_df['start_datetime'] < booking_end) & 
        (bookings_df['end_datetime'] > booking_start)
    ]

    # Calculate total places taken in the intersecting time segments
    total_places_taken = intersecting_bookings['places'].sum()

    # Calculate available places
    available_places = MAX_BOOKINGS_PER_HOUR - total_places_taken

    return max(0, available_places)  # Ensure we don't return negative values


def add_booking(user_id, booking_datetime, places=1):
    global bookings_df
    available_places = get_available_places(booking_datetime)
    
    if available_places < places:
        return False  # Not enough space available
    
    new_booking = pd.DataFrame({
        'user_id': [user_id],
        'date': [booking_datetime.date()],
        'time': [booking_datetime.time()],  # Use the exact time without rounding
        'places': [places]
    })
    bookings_df = pd.concat([bookings_df, new_booking], ignore_index=True)
    save_bookings()
    return True

def get_all_bookings():
    try:
        with open('bookings.json', 'r') as f:
            bookings = json.load(f)
        
        if not bookings:
            logging.info("Bookings file is empty.")
            return []

        # Convert string dates and times back to datetime objects
        for booking in bookings:
            booking['date'] = datetime.strptime(booking['date'], '%Y-%m-%d').date()
            booking['time'] = datetime.strptime(booking['time'], '%H:%M:%S').time()
        
        return bookings
    except FileNotFoundError:
        logging.info("Bookings file not found. Creating a new one.")
        with open('bookings.json', 'w') as f:
            json.dump([], f)
        return []
    except json.JSONDecodeError:
        logging.error("Error decoding JSON from bookings file. Starting with an empty list.")
        return []

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
    if not bookings:
        return []  # If bookings is empty, just return an empty list
    current_datetime = datetime.now()
    updated_bookings = [
        booking for booking in bookings
        if datetime.combine(booking['date'], booking['time']) > current_datetime
    ]
    save_bookings(updated_bookings)
    return updated_bookings

def get_user_data():
    try:
        df = pd.read_csv('users.csv')
        return dict(zip(df['user_id'], zip(df['name'], df['telegram_link'])))
    except FileNotFoundError:
        return {}
    

def get_user_name(user_id):
    try:
        df = pd.read_csv('users.csv')
        user_row = df[df['user_id'] == user_id]
        if not user_row.empty:
            return user_row['name'].iloc[0]
        else:
            return None
    except FileNotFoundError:
        return None
    except Exception as e:
        logging.error(f"Error retrieving user name: {e}")
        return None