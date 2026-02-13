import unittest

from reminder.domain.config import parse_active_hours


class ActiveHoursParserTest(unittest.TestCase):
    def test_empty_is_all_day(self) -> None:
        ranges, normalized = parse_active_hours("")
        self.assertEqual(ranges, [])
        self.assertEqual(normalized, "")

    def test_multiple_segments(self) -> None:
        ranges, normalized = parse_active_hours("9-12/13-18/19-21")
        self.assertEqual(ranges, [(9, 12), (13, 18), (19, 21)])
        self.assertEqual(normalized, "9-12/13-18/19-21")

    def test_invalid_segment_raises(self) -> None:
        with self.assertRaises(ValueError):
            parse_active_hours("abc")


if __name__ == "__main__":
    unittest.main()
