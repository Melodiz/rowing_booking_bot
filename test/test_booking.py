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

    # Find all bookings that overlap with our requested time slot
    overlapping_bookings = df[
        (df['start_datetime'] < booking_end) & 
        (df['end_datetime'] > booking_start)
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

class TestBooking(unittest.TestCase):
    def setUp(self):
        self.df = pd.DataFrame([
            {"user_id": 277218291, "date": "2025-02-24", "time": "19:00:00", "places": 4},
            {"user_id": 677265840, "date": "2025-02-24", "time": "20:00:00", "places": 2},
        ])

    def test_available_places(self):
        self.assertEqual(T_get_available_places(self.df, datetime(2025, 2, 24, 18, 0)), 6)
        self.assertEqual(T_get_available_places(self.df, datetime(2025, 2, 24, 18, 1)), 2)
        self.assertEqual(T_get_available_places(self.df, datetime(2025, 2, 24, 18, 59)), 2)
        self.assertEqual(T_get_available_places(self.df, datetime(2025, 2, 24, 19, 0)), 2)
        self.assertEqual(T_get_available_places(self.df, datetime(2025, 2, 24, 19, 1)), 2)
        self.assertEqual(T_get_available_places(self.df, datetime(2025, 2, 24, 19, 59)), 2)
        self.assertEqual(T_get_available_places(self.df, datetime(2025, 2, 24, 20, 0)), 4)
        self.assertEqual(T_get_available_places(self.df, datetime(2025, 2, 24, 20, 1)), 4)
        self.assertEqual(T_get_available_places(self.df, datetime(2025, 2, 24, 20, 59)), 4)
        self.assertEqual(T_get_available_places(self.df, datetime(2025, 2, 24, 21, 0)), 6)
        self.assertEqual(T_get_available_places(self.df, datetime(2025, 2, 28, 17, 0)), 6)
        self.assertEqual(T_get_available_places(self.df, datetime(2025, 3, 1, 12, 0)), 6)

    def test_complicated_cases(self):
        self.df = pd.DataFrame([
            {"user_id": 1241016050, "date": "2025-02-24", "time": "19:00:00", "places": 2},
            {"user_id": 277218291, "date": "2025-02-24", "time": "19:30:00", "places": 2},
            {"user_id": 677265840, "date": "2025-02-24", "time": "20:00:00", "places": 2},
            {"user_id": 1729489075, "date": "2025-02-24", "time": "20:30:00", "places": 3}
        ])

        self.assertEqual(T_get_available_places(self.df, datetime(2025, 2, 24, 19, 0)), 2)
        self.assertEqual(T_get_available_places(self.df, datetime(2025, 2, 24, 19, 1)), 2)
        self.assertEqual(T_get_available_places(self.df, datetime(2025, 2, 24, 19, 30)), 2)
        self.assertEqual(T_get_available_places(self.df, datetime(2025, 2, 24, 19, 59)), 1)
        self.assertEqual(T_get_available_places(self.df, datetime(2025, 2, 24, 20, 00)), 1)
        self.assertEqual(T_get_available_places(self.df, datetime(2025, 2, 24, 20, 1)), 1)
        self.assertEqual(T_get_available_places(self.df, datetime(2025, 2, 24, 20, 30)), 1)
        self.assertEqual(T_get_available_places(self.df, datetime(2025, 2, 24, 20, 59)), 1)
        self.assertEqual(T_get_available_places(self.df, datetime(2025, 2, 24, 21, 00)), 3)



if __name__ == '__main__':
    unittest.main()
