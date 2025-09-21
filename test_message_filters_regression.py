#!/usr/bin/env python3
"""
Automated Regression Test Suite for Message Filters
This suite tests all message filtering functionality to prevent regressions.
"""

import sqlite3
import requests
import json
from datetime import datetime, timedelta
import time
from typing import Dict, List, Any, Optional
import unittest

class MessageFilterRegressionTests(unittest.TestCase):
    """Regression tests for message filtering functionality."""

    @classmethod
    def setUpClass(cls):
        """Set up test environment once for all tests."""
        cls.base_url = "http://localhost:8084"
        cls.db_path = "signal_bot.db"

        # Run test data generator first
        print("Setting up test data...")
        import subprocess
        result = subprocess.run(["python3", "test_filter_data_generator.py"],
                              capture_output=True, text=True)
        if result.returncode != 0:
            raise Exception(f"Failed to generate test data: {result.stderr}")
        print("Test data generated successfully")

    def setUp(self):
        """Set up before each test."""
        self.session = requests.Session()

    def tearDown(self):
        """Clean up after each test."""
        self.session.close()

    def get_messages(self, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Get messages from the API with given parameters."""
        url = f"{self.base_url}/api/messages"
        response = self.session.get(url, params=params or {})
        response.raise_for_status()
        return response.json()

    def get_message_count_from_db(self, group_id: Optional[str] = None,
                                 sender_uuid: Optional[str] = None,
                                 start_date: Optional[str] = None,
                                 end_date: Optional[str] = None,
                                 attachments_only: bool = False) -> int:
        """Get message count directly from database for verification."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        conditions = []
        params = []

        if group_id:
            conditions.append("group_id = ?")
            params.append(group_id)
        else:
            # Only monitored groups by default
            conditions.append("group_id IN (SELECT group_id FROM groups WHERE is_monitored = 1)")

        if sender_uuid:
            conditions.append("sender_uuid = ?")
            params.append(sender_uuid)

        if start_date:
            # Convert to timestamp (assuming UTC for test)
            start_ts = int(datetime.strptime(start_date, "%Y-%m-%d").timestamp() * 1000)
            conditions.append("timestamp >= ?")
            params.append(start_ts)

        if end_date:
            # End of day timestamp
            end_ts = int((datetime.strptime(end_date, "%Y-%m-%d") +
                         timedelta(days=1)).timestamp() * 1000)
            conditions.append("timestamp < ?")
            params.append(end_ts)

        if attachments_only:
            conditions.append("EXISTS (SELECT 1 FROM attachments WHERE message_id = messages.id)")

        where_clause = " AND ".join(conditions) if conditions else "1=1"
        query = f"SELECT COUNT(*) FROM messages WHERE {where_clause}"

        cursor.execute(query, params)
        count = cursor.fetchone()[0]
        conn.close()
        return count

    # ============== GROUP FILTER TESTS ==============

    def test_group_filter_all_groups(self):
        """Test that 'All Groups' shows messages from all monitored groups."""
        result = self.get_messages()

        # Should show messages from Test Group Alpha and Beta (monitored)
        # but NOT from Test Group Gamma (unmonitored)
        expected_count = self.get_message_count_from_db()

        self.assertEqual(result['total'], expected_count,
                        f"All Groups filter should show {expected_count} messages from monitored groups")

    def test_group_filter_specific_group(self):
        """Test filtering by specific group."""
        # Test Group Alpha
        result = self.get_messages({'group_id': 'TEST_GROUP_1'})
        expected_count = self.get_message_count_from_db(group_id='TEST_GROUP_1')

        self.assertEqual(result['total'], expected_count,
                        f"Group filter for TEST_GROUP_1 should show {expected_count} messages")

        # Test Group Beta
        result = self.get_messages({'group_id': 'TEST_GROUP_2'})
        expected_count = self.get_message_count_from_db(group_id='TEST_GROUP_2')

        self.assertEqual(result['total'], expected_count,
                        f"Group filter for TEST_GROUP_2 should show {expected_count} messages")

    def test_unmonitored_group_not_in_default(self):
        """Test that unmonitored groups don't appear in default view."""
        result = self.get_messages()

        # Verify no messages from TEST_GROUP_3 (unmonitored)
        messages_from_gamma = [msg for msg in result.get('messages', [])
                              if msg.get('group_id') == 'TEST_GROUP_3']

        self.assertEqual(len(messages_from_gamma), 0,
                        "Unmonitored group messages should not appear in default view")

    # ============== ATTACHMENTS FILTER TESTS ==============

    def test_attachments_only_filter(self):
        """Test attachments only filter."""
        result = self.get_messages({'attachments_only': 'true'})
        expected_count = self.get_message_count_from_db(attachments_only=True)

        self.assertGreater(expected_count, 0, "Should have messages with attachments in test data")
        self.assertEqual(result['total'], expected_count,
                        f"Attachments filter should show {expected_count} messages")

        # Verify all returned messages have attachments
        for message in result.get('messages', []):
            self.assertTrue(message.get('has_attachment') or message.get('attachments'),
                          f"Message {message.get('id')} should have attachment")

    # ============== DATE FILTER TESTS ==============

    def test_today_filter(self):
        """Test 'Today' date filter - KNOWN BUG."""
        today = datetime.now().strftime("%Y-%m-%d")
        result = self.get_messages({'date': today, 'date_mode': 'today'})

        # This test documents the bug - "Today" filter shows yesterday's messages
        for message in result.get('messages', [])[:5]:  # Check first 5 messages
            msg_date = datetime.fromtimestamp(message['timestamp'] / 1000).strftime("%Y-%m-%d")

            # Currently failing - documents the bug
            if msg_date != today:
                self.fail(f"BUG CONFIRMED: 'Today' filter shows message from {msg_date} instead of {today}")

    def test_specific_date_filter(self):
        """Test specific date filtering."""
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        result = self.get_messages({'date': yesterday, 'date_mode': 'specific'})

        # Verify messages are from the specified date
        for message in result.get('messages', [])[:5]:
            msg_date = datetime.fromtimestamp(message['timestamp'] / 1000).strftime("%Y-%m-%d")
            self.assertEqual(msg_date, yesterday,
                           f"Message should be from {yesterday}, but is from {msg_date}")

    # ============== COMBINED FILTER TESTS ==============

    def test_combined_group_and_attachments(self):
        """Test combining group and attachments filters."""
        result = self.get_messages({
            'group_id': 'TEST_GROUP_1',
            'attachments_only': 'true'
        })

        expected_count = self.get_message_count_from_db(
            group_id='TEST_GROUP_1',
            attachments_only=True
        )

        self.assertEqual(result['total'], expected_count,
                        f"Combined filter should show {expected_count} messages")

        # Verify all messages match both criteria
        for message in result.get('messages', []):
            self.assertEqual(message['group_id'], 'TEST_GROUP_1',
                          "Message should be from TEST_GROUP_1")
            self.assertTrue(message.get('has_attachment') or message.get('attachments'),
                          "Message should have attachment")

    def test_combined_group_date_attachments(self):
        """Test combining multiple filters."""
        today = datetime.now().strftime("%Y-%m-%d")
        result = self.get_messages({
            'group_id': 'TEST_GROUP_1',
            'date': today,
            'date_mode': 'specific',
            'attachments_only': 'true'
        })

        # All messages should match all three criteria
        for message in result.get('messages', []):
            msg_date = datetime.fromtimestamp(message['timestamp'] / 1000).strftime("%Y-%m-%d")
            self.assertEqual(message['group_id'], 'TEST_GROUP_1')
            self.assertEqual(msg_date, today)
            self.assertTrue(message.get('has_attachment') or message.get('attachments'))

    # ============== HOURS FILTER TESTS ==============

    def test_hours_filter_24h(self):
        """Test 24 hours filter."""
        result = self.get_messages({'hours': '24'})

        cutoff_time = datetime.now() - timedelta(hours=24)

        # Verify all messages are within last 24 hours
        for message in result.get('messages', [])[:10]:
            msg_time = datetime.fromtimestamp(message['timestamp'] / 1000)
            self.assertGreaterEqual(msg_time, cutoff_time,
                                  f"Message should be within last 24 hours")

    def test_hours_filter_various(self):
        """Test various hour filters."""
        hour_options = [1, 3, 6, 12, 24, 48]

        for hours in hour_options:
            result = self.get_messages({'hours': str(hours)})
            cutoff_time = datetime.now() - timedelta(hours=hours)

            # Check at least first message is within range
            if result.get('messages'):
                first_msg_time = datetime.fromtimestamp(result['messages'][0]['timestamp'] / 1000)
                self.assertGreaterEqual(first_msg_time, cutoff_time,
                                      f"First message should be within last {hours} hours")

    # ============== PAGINATION TESTS ==============

    def test_pagination(self):
        """Test pagination functionality."""
        # Get first page
        page1 = self.get_messages({'page': '1', 'limit': '10'})
        self.assertLessEqual(len(page1.get('messages', [])), 10,
                           "Page should have at most 10 messages")

        # Get second page
        page2 = self.get_messages({'page': '2', 'limit': '10'})

        # Ensure pages have different messages
        if page1.get('messages') and page2.get('messages'):
            page1_ids = {msg['id'] for msg in page1['messages']}
            page2_ids = {msg['id'] for msg in page2['messages']}
            self.assertEqual(len(page1_ids & page2_ids), 0,
                          "Pages should not have overlapping messages")

    # ============== RESET FILTER TEST ==============

    def test_reset_filters(self):
        """Test that reset returns to default state."""
        # First apply filters
        filtered = self.get_messages({
            'group_id': 'TEST_GROUP_1',
            'attachments_only': 'true'
        })

        # Then reset (no params)
        reset = self.get_messages()

        # Should show more messages after reset
        self.assertGreater(reset['total'], filtered['total'],
                         "Reset should show more messages than filtered view")

    # ============== ERROR HANDLING TESTS ==============

    def test_invalid_group_id(self):
        """Test handling of invalid group ID."""
        result = self.get_messages({'group_id': 'INVALID_GROUP'})
        self.assertEqual(result['total'], 0,
                        "Invalid group should return 0 messages")

    def test_invalid_date_format(self):
        """Test handling of invalid date format."""
        try:
            result = self.get_messages({'date': 'invalid-date'})
            # Should either handle gracefully or raise error
        except Exception as e:
            # Document the error handling
            self.assertIn('date', str(e).lower(),
                        "Error should mention date issue")


def run_regression_tests():
    """Run all regression tests and generate report."""
    # Create test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(MessageFilterRegressionTests)

    # Run tests with detailed output
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Generate summary report
    print("\n" + "="*60)
    print("REGRESSION TEST SUMMARY")
    print("="*60)
    print(f"Tests Run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success Rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")

    if result.failures:
        print("\nFAILED TESTS:")
        for test, traceback in result.failures:
            print(f"  - {test}")

    if result.errors:
        print("\nERROR TESTS:")
        for test, traceback in result.errors:
            print(f"  - {test}")

    print("="*60)

    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_regression_tests()
    exit(0 if success else 1)