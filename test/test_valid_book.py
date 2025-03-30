import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from source.valid_book import is_valid_booking_time
from datetime import datetime, timedelta


def test_is_valid_booking_time():
    test_cases = [
        (datetime(2023, 6, 5, 8, 0), 60),  # Monday 8:00 AM (should be valid)
        (datetime(2023, 6, 5, 6, 0), 60),  # Monday 6:00 AM (should be invalid)
        # Monday 9:30 PM (should be invalid)
        (datetime(2023, 6, 5, 21, 30), 60),
        # Saturday 10:00 AM (should be valid)
        (datetime(2023, 6, 10, 10, 0), 60),
        # Sunday 12:00 PM (should be invalid)
        (datetime(2023, 6, 11, 12, 0), 60),
    ]

    for test_datetime, duration in test_cases:
        is_valid, message = is_valid_booking_time(test_datetime, duration)
        print(
            f"Booking at {test_datetime}: {'Valid' if is_valid else 'Invalid'}")
        if not is_valid:
            print(f"Message: {message}")
        print()

    # Test different durations
    test_datetime = datetime(2023, 6, 5, 21, 0)  # Monday 9:00 PM
    for duration in [30, 60, 90, 120]:
        is_valid, message = is_valid_booking_time(test_datetime, duration)
        print(
            f"Booking at {test_datetime} for {duration} minutes: {'Valid' if is_valid else 'Invalid'}")
        if not is_valid:
            print(f"Message: {message}")
        print()

    print("\nTesting gym closure period:")
    closure_test_cases = [
        datetime(2025, 3, 20, 12, 0),  # Before closure
        datetime(2025, 3, 25, 12, 0),  # During closure
        datetime(2025, 4, 1, 12, 0),   # After closure
    ]

    for test_datetime in closure_test_cases:
        is_valid, message = is_valid_booking_time(test_datetime)
        print(
            f"Booking at {test_datetime}: {'Valid' if is_valid else 'Invalid'}")
        if not is_valid:
            print(f"Message: {message}")
        print()

if __name__ == "__main__":
    test_is_valid_booking_time()