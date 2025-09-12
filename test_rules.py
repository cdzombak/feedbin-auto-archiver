#!/usr/bin/env python3
"""
Comprehensive test suite for feedbin_archiver Rules class.

Tests the rule logic including:
- Feed-specific rules
- Title regex rules  
- Aggressive rule prioritization (smallest values win)
- Edge cases and error handling
"""

import sys
import datetime as dt
from feedbin_archiver import Rules

def test_basic_feed_rules():
    """Test basic feed-specific rules."""
    print("Testing basic feed-specific rules...")
    
    rules = Rules(30)  # default max_age = 30
    rules.add_rules({
        "feed_specific": [
            {"feed_id": 100, "max_age": 5},
            {"feed_id": 200, "keep_n": 3},
            {"feed_id": 300, "max_age": 10, "keep_n": 2}
        ]
    })
    
    # Test feed-specific max_age
    assert rules.max_age(100).days == 5
    assert rules.max_age(999).days == 30  # default
    
    # Test feed-specific keep_n
    assert rules.keep_n(200) == 3
    assert rules.keep_n(999) is None  # no keep_n rule
    
    # Test feed with both
    assert rules.max_age(300).days == 10
    assert rules.keep_n(300) == 2
    
    # Test uses_* methods
    assert rules.uses_keep_n(200) == True
    assert rules.uses_keep_n(100) == False
    assert rules.uses_max_age(100) == True
    assert rules.uses_max_age(200) == False  # uses keep_n instead
    
    print("✓ Basic feed-specific rules work correctly")

def test_basic_title_regex_rules():
    """Test basic title regex rules."""
    print("Testing basic title regex rules...")
    
    rules = Rules(30)
    rules.add_rules({
        "title_regex": [
            {"title_regex": "Daily", "max_age": 3},
            {"title_regex": "Newsletter", "keep_n": 2},
            {"title_regex": "(?i)blog$", "max_age": 7, "keep_n": 5}
        ]
    })
    
    # Test title regex max_age
    assert rules.max_age(100, "Daily News").days == 3
    assert rules.max_age(100, "Random Feed").days == 30  # default
    
    # Test title regex keep_n
    assert rules.keep_n(100, "Weekly Newsletter") == 2
    assert rules.keep_n(100, "Random Feed") is None
    
    # Test case-insensitive regex
    assert rules.max_age(100, "My Personal Blog").days == 7
    assert rules.keep_n(100, "My Personal Blog") == 5
    
    # Test uses_* methods with titles
    assert rules.uses_keep_n(100, "Newsletter") == True
    assert rules.uses_keep_n(100, "Daily News") == False
    assert rules.uses_max_age(100, "Daily News") == True
    
    print("✓ Basic title regex rules work correctly")

def test_aggressive_prioritization():
    """Test that most aggressive rules win when multiple rules apply."""
    print("Testing aggressive rule prioritization...")
    
    rules = Rules(30)
    rules.add_rules({
        "feed_specific": [
            {"feed_id": 100, "max_age": 10},
            {"feed_id": 200, "keep_n": 8}
        ],
        "title_regex": [
            {"title_regex": "Daily", "max_age": 3},
            {"title_regex": "Newsletter", "keep_n": 2},
            {"title_regex": "Breaking", "max_age": 1, "keep_n": 1}
        ]
    })
    
    # Feed-specific vs title regex - most aggressive wins
    assert rules.max_age(100, "Daily Update").days == 3  # 3 < 10
    assert rules.keep_n(200, "Weekly Newsletter") == 2   # 2 < 8
    
    # Multiple title regex rules - most aggressive wins  
    assert rules.max_age(300, "Daily Breaking News").days == 1  # min(3, 1) = 1
    assert rules.keep_n(300, "Breaking Newsletter") == 1        # min(2, 1) = 1
    
    # All types combined
    assert rules.max_age(100, "Daily Breaking News").days == 1  # min(10, 3, 1) = 1
    assert rules.keep_n(200, "Breaking Newsletter") == 1        # min(8, 2, 1) = 1
    
    print("✓ Aggressive rule prioritization works correctly")

def test_edge_cases():
    """Test edge cases and error handling.""" 
    print("Testing edge cases...")
    
    # Test with no rules defined
    rules = Rules(15)
    rules.add_rules({"feed_specific": []})
    assert rules.max_age(100).days == 15
    assert rules.keep_n(100) is None
    
    # Test only_feed_id filtering
    rules = Rules(10, only_feed_id=100)
    rules.add_rules({"feed_specific": [{"feed_id": 100, "max_age": 5}]})
    assert rules.max_age(100).days == 5
    assert rules.max_age(200) == dt.timedelta.max  # filtered out
    
    # Test invalid regex
    try:
        rules = Rules(10)
        rules.add_rules({"title_regex": [{"title_regex": "[invalid", "max_age": 1}]})
        assert False, "Should have raised SpecException"
    except Rules.SpecException:
        pass  # Expected
    
    # Test missing required fields
    try:
        rules = Rules(10)
        rules.add_rules({"feed_specific": [{"feed_id": 100}]})  # missing max_age/keep_n
        assert False, "Should have raised SpecException"
    except Rules.SpecException:
        pass  # Expected
    
    try:
        rules = Rules(10) 
        rules.add_rules({"title_regex": [{"title_regex": "test"}]})  # missing max_age/keep_n
        assert False, "Should have raised SpecException"
    except Rules.SpecException:
        pass  # Expected
    
    print("✓ Edge cases handled correctly")

def test_rule_combinations():
    """Test various combinations of rules to ensure correctness."""
    print("Testing rule combinations...")
    
    rules = Rules(30)
    rules.add_rules({
        "max_age": 25,  # Override default
        "feed_specific": [
            {"feed_id": 100, "max_age": 5},
            {"feed_id": 200, "keep_n": 10}
        ],
        "title_regex": [
            {"title_regex": "Important", "max_age": 15, "keep_n": 12},
            {"title_regex": "Urgent", "max_age": 2},
            {"title_regex": "Archive", "keep_n": 1}
        ]
    })
    
    # Global max_age override
    assert rules.max_age(999).days == 25
    
    # Feed + multiple regex matches
    feed_title = "Important Urgent News"
    assert rules.max_age(100, feed_title).days == 2   # min(5, 15, 2) = 2
    assert rules.keep_n(200, feed_title) == 10        # min(10, 12) = 10
    
    # Just regex matches
    assert rules.max_age(300, "Important Archive").days == 15  # min(25, 15) = 15
    assert rules.keep_n(300, "Important Archive") == 1         # min(12, 1) = 1
    
    # Mix of rules with some not applying
    assert rules.max_age(400, "Urgent Update").days == 2     # min(25, 2) = 2
    assert rules.keep_n(400, "Archive This") == 1            # only Archive applies
    
    print("✓ Rule combinations work correctly")

def run_all_tests():
    """Run all tests and return success status."""
    try:
        test_basic_feed_rules()
        test_basic_title_regex_rules()  
        test_aggressive_prioritization()
        test_edge_cases()
        test_rule_combinations()
        return True
    except Exception as e:
        print(f"✗ Test failed: {e}")
        return False

if __name__ == "__main__":
    print("Running feedbin_archiver Rules test suite...\n")
    
    if run_all_tests():
        print(f"\n🎉 All tests passed!")
        sys.exit(0)
    else:
        print(f"\n💥 Some tests failed!")
        sys.exit(1)