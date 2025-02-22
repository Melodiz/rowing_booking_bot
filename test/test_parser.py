import unittest
import sys, os
from datetime import datetime, time, timedelta
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from source.datetime_parser import parse_date, parse_time, parse_amount, parse_booking_datetime


class TestDatetimeParser(unittest.TestCase):
    def setUp(self):
        self.current_date = datetime(2024, 2, 22)  # Assuming current date is March 15, 2024

    def test_parse_date(self):
        # Test dd.mm format
        self.assertEqual(parse_date("20.03", self.current_date), datetime(2024, 3, 20).date())
        self.assertEqual(parse_date("01.03", self.current_date), datetime(2024, 3, 1).date())
        
        # Test dd/mm format
        self.assertEqual(parse_date("25/04", self.current_date), datetime(2024, 4, 25).date())
        self.assertEqual(parse_date("25/02", self.current_date), datetime(2024, 2, 25).date())
        
        # Test dd format
        self.assertEqual(parse_date("10", self.current_date), datetime(2024, 3, 10).date())
        self.assertEqual(parse_date("28", self.current_date), datetime(2024, 2, 28).date())
        self.assertEqual(parse_date("27", self.current_date), datetime(2024, 2, 27).date())
        self.assertEqual(parse_date("22", self.current_date), datetime(2024, 2, 22).date())
        
        # Test invalid dates
        self.assertIsNone(parse_date("32.03", self.current_date))
        self.assertIsNone(parse_date("25/13", self.current_date))
        self.assertIsNone(parse_date("00", self.current_date))
        
        # Test invalid format
        self.assertIsNone(parse_date("2024-03-20", self.current_date))

    def test_parse_time(self):
        # Test hh:mm format
        self.assertEqual(parse_time("14:30"), time(14, 30))
        
        # Test hh.mm format
        self.assertEqual(parse_time("09.45"), time(9, 45))
        
        # Test hhmm format
        self.assertEqual(parse_time("2215"), time(22, 15))
        self.assertEqual(parse_time("0115"), time(1, 15))
        self.assertEqual(parse_time("1500"), time(15, 00))
        
        # Test invalid times
        self.assertIsNone(parse_time("25:00"))
        self.assertIsNone(parse_time("14:60"))
        self.assertIsNone(parse_time("2500"))
        
        # Test invalid format
        self.assertIsNone(parse_time("14-30"))

    def test_parse_amount(self):
        self.assertEqual(parse_amount("5"), 5)
        self.assertEqual(parse_amount("10"), 10)
        self.assertEqual(parse_amount("invalid"), 1)  # Default to 1 for invalid input

    def test_parse_booking_datetime(self):
        now = datetime.now()
        current_year = now.year
        
        # Test time only
        result, amount = parse_booking_datetime("14:30")
        self.assertEqual(result.time(), time(14, 30))
        self.assertEqual(amount, 1)
        
        # Test time with amount
        result, amount = parse_booking_datetime("15:45 3")
        self.assertEqual(result.time(), time(15, 45))
        self.assertEqual(amount, 3)
        
        # Test time with 'k' amount
        result, amount = parse_booking_datetime("16:00 2")
        self.assertEqual(result.time(), time(16, 0))
        self.assertEqual(amount, 2)
        
        # Test invalid time
        result, amount = parse_booking_datetime("25:00")
        self.assertIsNone(result)
        self.assertIsNone(amount)

        test_cases = [
            # Original test cases with 'k' (amount)
            ("22.03 14.30 3", datetime(current_year, 3, 22, 14, 30), 3),
            ("22/03 14.30 4", datetime(current_year, 3, 22, 14, 30), 4),
            ("22.03 14:30 5", datetime(current_year, 3, 22, 14, 30), 5),
            ("22/03 14:30 6", datetime(current_year, 3, 22, 14, 30), 6),
            ("22.03 1430 2", datetime(current_year, 3, 22, 14, 30), 2),
            ("22/03 1430 1", datetime(current_year, 3, 22, 14, 30), 1),
            ("22 14.30 3", datetime(current_year, 3, 22, 14, 30), 3),
            ("22 14:30 4", datetime(current_year, 3, 22, 14, 30), 4),
            ("22 1430 5", datetime(current_year, 3, 22, 14, 30), 5),
            ("25 14.30 3", datetime(current_year, now.month, 25, 14, 30), 3),
            ("25 14:30 4", datetime(current_year, now.month, 25, 14, 30), 4),
            ("25 1430 5", datetime(current_year, now.month, 25, 14, 30), 5),
            ("1430 6", datetime(now.year, now.month, now.day, 14, 30), 6),
            ("14:30 2", datetime(now.year, now.month, now.day, 14, 30), 2),
            ("14.30 1", datetime(now.year, now.month, now.day, 14, 30), 1),
            
            # New test cases without 'k' (amount) - should default to 1
            ("22.03 14.30", datetime(current_year, 3, 22, 14, 30), 1),
            ("22/03 14.30", datetime(current_year, 3, 22, 14, 30), 1),
            ("22.03 14:30", datetime(current_year, 3, 22, 14, 30), 1),
            ("22/03 14:30", datetime(current_year, 3, 22, 14, 30), 1),
            ("22.03 1430", datetime(current_year, 3, 22, 14, 30), 1),
            ("22/03 1430", datetime(current_year, 3, 22, 14, 30), 1),
            ("22 14.30", datetime(current_year, 3, 22, 14, 30), 1),
            ("22 14:30", datetime(current_year, 3, 22, 14, 30), 1),
            ("22 1430", datetime(current_year, 3, 22, 14, 30), 1),
            ("25 14.30", datetime(current_year, now.month, 25, 14, 30), 1),
            ("25 14:30", datetime(current_year, now.month, 25, 14, 30), 1),
            ("25 1430", datetime(current_year, now.month, 25, 14, 30), 1),
            ("1430", datetime(now.year, now.month, now.day, 14, 30), 1),
            ("14:30", datetime(now.year, now.month, now.day, 14, 30), 1),
            ("14.30", datetime(now.year, now.month, now.day, 14, 30), 1),
        ]

        for input_str, expected_datetime, expected_amount in test_cases:
            result, amount = parse_booking_datetime(input_str)
            self.assertEqual(result, expected_datetime, f"Failed for input: {input_str}")
            self.assertEqual(amount, expected_amount, f"Failed for input: {input_str}")

        # Test invalid inputs
        invalid_inputs = [
            "32.03 14:30 3",  # Invalid date
            "22.13 14:30 3",  # Invalid month
            "22.03 25:30 3",  # Invalid hour
            "22.03 14:60 3",  # Invalid minute
        ]

        for invalid_input in invalid_inputs:
            result, amount = parse_booking_datetime(invalid_input)
            self.assertIsNone(result, f"Should be None for invalid input: {invalid_input}")
            self.assertIsNone(amount, f"Should be None for invalid input: {invalid_input}")


if __name__ == '__main__':
    unittest.main()