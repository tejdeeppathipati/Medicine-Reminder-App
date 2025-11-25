"""
Unit tests for the current simple medication parsing stub.
"""
import unittest
from backend.aiParsing import aiParseMedicine


class TestAIParsing(unittest.TestCase):
    """Test cases for simple medication parsing"""

    def test_parse_name_time_day(self):
        result = aiParseMedicine("vitamind 7:41pm friday")
        self.assertEqual(result["medicine_name"], "vitamind")
        self.assertEqual(result["time"], "7:41pm")
        self.assertEqual(result["day"], "friday")

    def test_parse_name_and_time_only(self):
        result = aiParseMedicine("aspirin 9am")
        self.assertEqual(result["medicine_name"], "aspirin")
        self.assertEqual(result["time"], "9am")
        self.assertEqual(result["day"], "")

    def test_parse_requires_at_least_two_tokens(self):
        with self.assertRaises(ValueError):
            aiParseMedicine("aspirin") 


if __name__ == "__main__":
    unittest.main()
