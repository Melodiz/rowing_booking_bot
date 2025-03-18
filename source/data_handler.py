import pandas as pd
import json
import logging
from datetime import datetime, timedelta, date, time
import os
import requests


BOOKINGS_FILE = 'bookings.json'
bookings_df = pd.DataFrame(columns=['user_id', 'date', 'time', 'places', 'duration'])

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
                # Ensure duration column exists, default to 60 minutes if not present
                if 'duration' not in bookings_df.columns:
                    bookings_df['duration'] = 60
            else:
                bookings_df = pd.DataFrame(columns=['user_id', 'date', 'time', 'places', 'duration'])
    except FileNotFoundError:
        logging.info("Bookings file not found. Starting with an empty DataFrame.")
        bookings_df = pd.DataFrame(columns=['user_id', 'date', 'time', 'places', 'duration'])
    except json.JSONDecodeError:
        logging.error("Error decoding JSON from bookings file. Starting with an empty DataFrame.")
        bookings_df = pd.DataFrame(columns=['user_id', 'date', 'time', 'places', 'duration'])


def save_bookings(updated_bookings=None):
    global bookings_df
    if updated_bookings is not None:
        bookings_df = pd.DataFrame(updated_bookings)
        # Ensure duration column exists
        if 'duration' not in bookings_df.columns:
            bookings_df['duration'] = 60
    
    # Convert date and time objects to strings
    bookings_data = bookings_df.to_dict('records')
    for booking in bookings_data:
        if isinstance(booking['date'], date):
            booking['date'] = booking['date'].isoformat()
        if isinstance(booking['time'], time):
            booking['time'] = booking['time'].isoformat()
    
    with open(BOOKINGS_FILE, 'w') as file:
        json.dump(bookings_data, file, default=str)


def add_booking(user_id, booking_datetime, places=1, duration=60):
    global bookings_df
    available_places = get_available_places(booking_datetime, duration)
    
    if available_places < places:
        return False  # Not enough space available
    
    new_booking = pd.DataFrame({
        'user_id': [user_id],
        'date': [booking_datetime.date()],
        'time': [booking_datetime.time()], 
        'places': [places], 
        'duration': [duration]
    })
    bookings_df = pd.concat([bookings_df, new_booking], ignore_index=True)
    save_bookings()
    return True


def is_space_available(booking_datetime, duration=60):
    available_places = get_available_places(booking_datetime, duration)
    return available_places > 0


def get_available_places(booking_datetime, duration=60):
    remove_old_bookings()
    global bookings_df
    if bookings_df.empty:
        return MAX_BOOKINGS_PER_HOUR

    # Convert date strings to datetime objects
    bookings_df['start_datetime'] = pd.to_datetime(bookings_df['date'].astype(str) + ' ' + bookings_df['time'].astype(str))
    
    # Ensure duration column exists
    if 'duration' not in bookings_df.columns:
        bookings_df['duration'] = 60
    
    # Calculate end datetime based on duration
    bookings_df['end_datetime'] = bookings_df.apply(
        lambda row: row['start_datetime'] + timedelta(minutes=row['duration']), 
        axis=1
    )

    # Define the booking time range
    booking_start = booking_datetime
    booking_end = booking_start + timedelta(minutes=duration)

    # Find all bookings that overlap with our requested time slot
    overlapping_bookings = bookings_df[
        (bookings_df['start_datetime'] < booking_end) & 
        (bookings_df['end_datetime'] > booking_start)
    ]
    
    if overlapping_bookings.empty:
        return MAX_BOOKINGS_PER_HOUR
    
    # Create a list of all time points where occupancy changes
    critical_times = []
    for _, booking in overlapping_bookings.iterrows():
        # Only consider critical times within our booking window
        if booking['start_datetime'] >= booking_start and booking['start_datetime'] < booking_end:
            critical_times.append((booking['start_datetime'], booking['places']))
        if booking['end_datetime'] > booking_start and booking['end_datetime'] <= booking_end:
            critical_times.append((booking['end_datetime'], -booking['places']))  # Negative because places are freed
    
    # Add the booking start and end times if they're not already included
    critical_times.append((booking_start, 0))
    critical_times.append((booking_end, 0))
    
    # Sort by time
    critical_times.sort()
    
    # Calculate maximum occupancy during the requested time slot
    current_occupancy = 0
    max_occupancy = 0
    
    # First, calculate occupancy at booking_start from existing bookings
    for _, booking in overlapping_bookings.iterrows():
        if booking['start_datetime'] <= booking_start and booking['end_datetime'] > booking_start:
            current_occupancy += booking['places']
    
    max_occupancy = current_occupancy
    
    # Then process all critical points to find maximum occupancy
    for time, change in critical_times:
        if time > booking_start:  # Skip the initial state we already calculated
            current_occupancy += change
            max_occupancy = max(max_occupancy, current_occupancy)
    
    # Calculate available places based on maximum occupancy
    available_places = MAX_BOOKINGS_PER_HOUR - max_occupancy
    
    return max(0, available_places)  # Ensure we don't return negative values

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
            # Ensure duration exists
            if 'duration' not in booking:
                booking['duration'] = 60
        
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
    updated_bookings = []
    
    for booking in bookings:
        # Get the start datetime
        start_datetime = datetime.combine(booking['date'], booking['time'])
        
        # Calculate end datetime based on duration (default to 60 if not present)
        duration = booking.get('duration', 60)
        end_datetime = start_datetime + timedelta(minutes=duration)
        
        # Keep booking if end time is in the future
        if end_datetime > current_datetime:
            updated_bookings.append(booking)
        else:
            add_report(booking)
    
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
    
def add_report(booking):
    report_dir = "reports"
    if not os.path.exists(report_dir):
        os.makedirs(report_dir)

    user_data = get_user_data()
    user_id = booking['user_id']

    # Format time range
    booking_time = booking['time']
    duration = booking.get('duration', 60)
    start_datetime = datetime.combine(booking['date'], booking_time)
    end_datetime = start_datetime + timedelta(minutes=duration)
    time_range = f"{booking_time.strftime('%H:%M')}-{end_datetime.strftime('%H:%M')}"

    # Get user info
    if user_id in user_data:
        name, telegram_link = user_data[user_id]
        user_info = f"{name} ({telegram_link})"
    else:
        user_info = f"User ID: {user_id}"

    # Format places and duration
    places = booking.get('places', 1)

    # Create the formatted entry
    entry = f"- {time_range}: {user_info} - {places} places, {duration} min\n"

    # Prepare file path
    booking_day = booking['date'].strftime('%Y-%m-%d')
    formatted_date = booking['date'].strftime('%d.%m.%Y')
    filename = f"{report_dir}/{booking_day}.txt"

    # Check if file exists
    file_exists = os.path.isfile(filename)

    # If we're creating a new file, upload the previous day's report
    if not file_exists:
        # Find the most recent report file that's older than the current booking date
        try:
            # Get all report files
            report_files = [f for f in os.listdir(report_dir) if f.endswith('.txt')]

            # Filter files that are older than the current booking date
            booking_date = booking['date']
            older_reports = []

            for report_file in report_files:
                # Extract date from filename (format: YYYY-MM-DD.txt)
                file_date_str = report_file.split('.')[0]
                try:
                    file_date = datetime.strptime(file_date_str, '%Y-%m-%d').date()
                    if file_date < booking_date:
                        older_reports.append((file_date, report_file))
                except ValueError:
                    # Skip files with invalid date format
                    continue

            # Sort by date (newest first)
            older_reports.sort(reverse=True)

            # Upload the most recent older report if it exists
            if older_reports:
                most_recent_report = older_reports[0][1]
                report_path = os.path.join(report_dir, most_recent_report)
                logging.info(f"Uploading previous report: {report_path}")
                upload_to_yandex(report_path)
        except Exception as e:
            logging.error(f"Error while trying to upload previous report: {e}")
    
    # Open file in append mode with UTF-8 encoding
    with open(filename, 'a', encoding='utf-8') as f:
        # If file is new, add header
        if not file_exists:
            f.write(f"Report on {formatted_date}\n\n")

        # Write the booking entry
        f.write(entry)

def upload_to_yandex(file_path, yandex_token_path='ya_token.json'):
    """
    Upload a file to Yandex Disk.

    Args:
        file_path (str): Path to the file to upload
        yandex_token_path (str): Path to the file containing Yandex Disk OAuth token

    Returns:
        bool: True if upload was successful, False otherwise
    """    
    try:
        # Read the Yandex Disk OAuth token from JSON file
        with open(yandex_token_path, 'r') as token_file:
            token_data = json.load(token_file)

        # Extract the token from the JSON structure
        if isinstance(token_data, dict) and 'yandex_token' in token_data:
            token = token_data['yandex_token']
        else:
            # If it's not a dict with 'yandex_token' key, try using it directly
            token = token_data

        if not token or not isinstance(token, str):
            logging.error("Invalid Yandex Disk token format")
            return False

        # Check if file exists
        if not os.path.isfile(file_path):
            logging.error(f"File not found: {file_path}")
            return False

        # Get filename from path
        filename = os.path.basename(file_path)

        # Prepare headers with OAuth token
        headers = {
            'Authorization': f'OAuth {token}',
            'Content-Type': 'application/json'
        }

        # Step 1: Get upload URL
        get_url_api = 'https://cloud-api.yandex.net/v1/disk/resources/upload'
        params = {
            'path': f'/reports_test/{filename}',  # Upload to reports folder on Yandex Disk
            'overwrite': 'true'
        }

        response = requests.get(get_url_api, headers=headers, params=params)

        if response.status_code != 200:
            logging.error(f"Failed to get upload URL: {response.text}")
            return False

        # Extract the upload URL
        upload_url = response.json().get('href')

        if not upload_url:
            logging.error("No upload URL received from Yandex Disk API")
            return False

        # Step 2: Upload the file
        with open(file_path, 'rb') as file_to_upload:
            # Use binary mode for file upload to avoid encoding issues
            upload_response = requests.put(
                upload_url, 
                data=file_to_upload,
                headers={'Content-Type': 'text/plain; charset=utf-8'}  # Specify UTF-8 encoding
            )

        if upload_response.status_code == 201 or upload_response.status_code == 200:
            logging.info(f"Successfully uploaded {filename} to Yandex Disk")
            return True
        else:
            logging.error(f"Failed to upload file: {upload_response.text}")
            return False

    except FileNotFoundError as e:
        logging.error(f"File not found: {e}")
        return False
    except json.JSONDecodeError as e:
        logging.error(f"Error parsing JSON response: {e}")
        return False
    except requests.exceptions.RequestException as e:
        logging.error(f"Request error: {e}")
        return False
    except Exception as e:
        logging.error(f"Unexpected error during Yandex Disk upload: {e}")
        return False