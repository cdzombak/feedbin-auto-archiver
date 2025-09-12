#!/usr/bin/env python3
"""
Comprehensive test suite for feedbin_archiver Rules class.

Tests the rule logic including:
- Feed-specific rules
- Title regex rules
- Aggressive rule prioritization (smallest values win)
- Edge cases and error handling
"""

import datetime as dt
import unittest

from feedbin_archiver import Rules


class TestRules(unittest.TestCase):
    """Test cases for the Rules class."""

    def test_basic_feed_rules(self):
        """Test basic feed-specific rules."""
        rules = Rules(30)  # default max_age = 30
        rules.add_rules(
            {
                "feed_specific": [
                    {"feed_id": 100, "max_age": 5},
                    {"feed_id": 200, "keep_n": 3},
                    {"feed_id": 300, "max_age": 10, "keep_n": 2},
                ]
            }
        )

        # Test feed-specific max_age
        self.assertEqual(rules.max_age(100).days, 5)
        self.assertEqual(rules.max_age(999).days, 30)  # default

        # Test feed-specific keep_n
        self.assertEqual(rules.keep_n(200), 3)
        self.assertIsNone(rules.keep_n(999))  # no keep_n rule

        # Test feed with both
        self.assertEqual(rules.max_age(300).days, 10)
        self.assertEqual(rules.keep_n(300), 2)

        # Test uses_* methods
        self.assertTrue(rules.uses_keep_n(200))
        self.assertFalse(rules.uses_keep_n(100))
        self.assertTrue(rules.uses_max_age(100))
        self.assertFalse(rules.uses_max_age(200))  # uses keep_n instead

    def test_basic_title_regex_rules(self):
        """Test basic title regex rules."""
        rules = Rules(30)
        rules.add_rules(
            {
                "title_regex": [
                    {"title_regex": "Daily", "max_age": 3},
                    {"title_regex": "Newsletter", "keep_n": 2},
                    {"title_regex": "(?i)blog$", "max_age": 7, "keep_n": 5},
                ]
            }
        )

        # Test title regex max_age
        self.assertEqual(rules.max_age(100, "Daily News").days, 3)
        self.assertEqual(rules.max_age(100, "Random Feed").days, 30)  # default

        # Test title regex keep_n
        self.assertEqual(rules.keep_n(100, "Weekly Newsletter"), 2)
        self.assertIsNone(rules.keep_n(100, "Random Feed"))

        # Test case-insensitive regex
        self.assertEqual(rules.max_age(100, "My Personal Blog").days, 7)
        self.assertEqual(rules.keep_n(100, "My Personal Blog"), 5)

        # Test uses_* methods with titles
        self.assertTrue(rules.uses_keep_n(100, "Newsletter"))
        self.assertFalse(rules.uses_keep_n(100, "Daily News"))
        self.assertTrue(rules.uses_max_age(100, "Daily News"))

    def test_aggressive_prioritization(self):
        """Test that most aggressive rules win when multiple rules apply."""
        rules = Rules(30)
        rules.add_rules(
            {
                "feed_specific": [
                    {"feed_id": 100, "max_age": 10},
                    {"feed_id": 200, "keep_n": 8},
                ],
                "title_regex": [
                    {"title_regex": "Daily", "max_age": 3},
                    {"title_regex": "Newsletter", "keep_n": 2},
                    {"title_regex": "Breaking", "max_age": 1, "keep_n": 1},
                ],
            }
        )

        # Feed-specific vs title regex - most aggressive wins
        self.assertEqual(rules.max_age(100, "Daily Update").days, 3)  # 3 < 10
        self.assertEqual(rules.keep_n(200, "Weekly Newsletter"), 2)  # 2 < 8

        # Multiple title regex rules - most aggressive wins
        self.assertEqual(
            rules.max_age(300, "Daily Breaking News").days, 1
        )  # min(3, 1) = 1
        self.assertEqual(rules.keep_n(300, "Breaking Newsletter"), 1)  # min(2, 1) = 1

        # All types combined
        self.assertEqual(
            rules.max_age(100, "Daily Breaking News").days, 1
        )  # min(10, 3, 1) = 1
        self.assertEqual(
            rules.keep_n(200, "Breaking Newsletter"), 1
        )  # min(8, 2, 1) = 1

    def test_edge_cases(self):
        """Test edge cases and error handling."""
        # Test with no rules defined
        rules = Rules(15)
        rules.add_rules({"feed_specific": []})
        self.assertEqual(rules.max_age(100).days, 15)
        self.assertIsNone(rules.keep_n(100))

        # Test only_feed_id filtering
        rules = Rules(10, only_feed_id=100)
        rules.add_rules({"feed_specific": [{"feed_id": 100, "max_age": 5}]})
        self.assertEqual(rules.max_age(100).days, 5)
        self.assertEqual(rules.max_age(200), dt.timedelta.max)  # filtered out

        # Test invalid regex
        with self.assertRaises(Rules.SpecException):
            rules = Rules(10)
            rules.add_rules(
                {"title_regex": [{"title_regex": "[invalid", "max_age": 1}]}
            )

        # Test missing required fields
        with self.assertRaises(Rules.SpecException):
            rules = Rules(10)
            rules.add_rules(
                {"feed_specific": [{"feed_id": 100}]}
            )  # missing max_age/keep_n

        with self.assertRaises(Rules.SpecException):
            rules = Rules(10)
            rules.add_rules(
                {"title_regex": [{"title_regex": "test"}]}
            )  # missing max_age/keep_n

    def test_rule_combinations(self):
        """Test various combinations of rules to ensure correctness."""
        rules = Rules(30)
        rules.add_rules(
            {
                "max_age": 25,  # Override default
                "feed_specific": [
                    {"feed_id": 100, "max_age": 5},
                    {"feed_id": 200, "keep_n": 10},
                ],
                "title_regex": [
                    {"title_regex": "Important", "max_age": 15, "keep_n": 12},
                    {"title_regex": "Urgent", "max_age": 2},
                    {"title_regex": "Archive", "keep_n": 1},
                ],
            }
        )

        # Global max_age override
        self.assertEqual(rules.max_age(999).days, 25)

        # Feed + multiple regex matches
        feed_title = "Important Urgent News"
        self.assertEqual(rules.max_age(100, feed_title).days, 2)  # min(5, 15, 2) = 2
        self.assertEqual(rules.keep_n(200, feed_title), 10)  # min(10, 12) = 10

        # Just regex matches
        self.assertEqual(
            rules.max_age(300, "Important Archive").days, 15
        )  # min(25, 15) = 15
        self.assertEqual(rules.keep_n(300, "Important Archive"), 1)  # min(12, 1) = 1

        # Mix of rules with some not applying
        self.assertEqual(rules.max_age(400, "Urgent Update").days, 2)  # min(25, 2) = 2
        self.assertEqual(rules.keep_n(400, "Archive This"), 1)  # only Archive applies


if __name__ == "__main__":
    unittest.main(verbosity=2)
