import unittest
from datetime import datetime, timedelta
import pandas as pd

def T_get_available_places(df, booking_datetime):
    MAX_BOOKINGS_PER_HOUR = 6

    # Convert date strings to datetime objects
    df['start_datetime'] = pd.to_datetime(df['date'] + ' ' + df['time'])
    df['end_datetime'] = df['start_datetime'] + timedelta(hours=1)

    # Define the booking time range
    booking_start = booking_datetime
    booking_end = booking_start + timedelta(hours=1)

    # Calculate intersecting bookings
    intersecting_bookings = df[
        (df['start_datetime'] < booking_end) & 
        (df['end_datetime'] > booking_start)
    ]

    # Calculate total places taken in the intersecting time segments
    total_places_taken = intersecting_bookings['places'].sum()

    # Calculate available places
    available_places = MAX_BOOKINGS_PER_HOUR - total_places_taken

    return max(0, available_places)  # Ensure we don't return negative values


class TestBooking(unittest.TestCase):
    def setUp(self):
        self.df = pd.DataFrame([
            {"user_id": 1241016050, "date": "2025-02-24", "time": "19:00:00", "places": 1},
            {"user_id": 823322690, "date": "2025-02-24", "time": "19:00:00", "places": 1},
            {"user_id": 277218291, "date": "2025-02-24", "time": "19:00:00", "places": 2},
            {"user_id": 677265840, "date": "2025-02-24", "time": "20:00:00", "places": 1},
            {"user_id": 1729489075, "date": "2025-02-24", "time": "20:00:00", "places": 1}
        ])

    def test_available_places(self):
        self.assertEqual(T_get_available_places(self.df, datetime(2025, 2, 24, 18, 0)), 6)
        self.assertEqual(T_get_available_places(self.df, datetime(2025, 2, 24, 18, 1)), 2)
        self.assertEqual(T_get_available_places(self.df, datetime(2025, 2, 24, 18, 59)), 2)
        self.assertEqual(T_get_available_places(self.df, datetime(2025, 2, 24, 19, 0)), 2)
        self.assertEqual(T_get_available_places(self.df, datetime(2025, 2, 24, 19, 1)), 0)
        self.assertEqual(T_get_available_places(self.df, datetime(2025, 2, 24, 19, 59)), 0)
        self.assertEqual(T_get_available_places(self.df, datetime(2025, 2, 24, 20, 0)), 4)
        self.assertEqual(T_get_available_places(self.df, datetime(2025, 2, 24, 20, 1)), 4)
        self.assertEqual(T_get_available_places(self.df, datetime(2025, 2, 24, 20, 59)), 4)
        self.assertEqual(T_get_available_places(self.df, datetime(2025, 2, 24, 21, 0)), 6)
        self.assertEqual(T_get_available_places(self.df, datetime(2025, 2, 28, 17, 0)), 6)
        self.assertEqual(T_get_available_places(self.df, datetime(2025, 3, 1, 12, 0)), 6)

if __name__ == '__main__':
    unittest.main()
