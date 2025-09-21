#!/usr/bin/env python3
"""
Comprehensive Test Data Generator for Message Filtering
This script creates test data covering all possible filtering scenarios.
"""

import sqlite3
import random
import time
from datetime import datetime, timedelta
import uuid

class TestDataGenerator:
    def __init__(self, db_path="signal_bot.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()

        # Test data parameters
        self.test_groups = [
            {"id": "TEST_GROUP_1", "name": "Test Group Alpha", "monitored": True},
            {"id": "TEST_GROUP_2", "name": "Test Group Beta", "monitored": True},
            {"id": "TEST_GROUP_3", "name": "Test Group Gamma", "monitored": False},
        ]

        self.test_users = [
            {"uuid": str(uuid.uuid4()), "phone": "+1111111111", "name": "Test User 1"},
            {"uuid": str(uuid.uuid4()), "phone": "+2222222222", "name": "Test User 2"},
            {"uuid": str(uuid.uuid4()), "phone": "+3333333333", "name": "Test User 3"},
        ]

        self.message_scenarios = []

    def clean_test_data(self):
        """Remove any existing test data"""
        print("Cleaning existing test data...")

        # Delete test messages and related data
        for group in self.test_groups:
            self.cursor.execute("DELETE FROM messages WHERE group_id = ?", (group["id"],))
            self.cursor.execute("DELETE FROM groups WHERE group_id = ?", (group["id"],))

        for user in self.test_users:
            self.cursor.execute("DELETE FROM users WHERE phone_number = ?", (user["phone"],))

        self.conn.commit()
        print("Test data cleaned.")

    def create_test_groups_and_users(self):
        """Create test groups and users"""
        print("Creating test groups and users...")

        # Create test groups
        for group in self.test_groups:
            self.cursor.execute("""
                INSERT OR REPLACE INTO groups (group_id, group_name, is_monitored, created_at)
                VALUES (?, ?, ?, datetime('now'))
            """, (group["id"], group["name"], group["monitored"]))

        # Create test users
        for user in self.test_users:
            self.cursor.execute("""
                INSERT OR REPLACE INTO users (uuid, phone_number, friendly_name, contact_name, created_at)
                VALUES (?, ?, ?, ?, datetime('now'))
            """, (user["uuid"], user["phone"], user["name"], user["name"]))

        self.conn.commit()
        print(f"Created {len(self.test_groups)} groups and {len(self.test_users)} users.")

    def generate_test_messages(self):
        """Generate comprehensive test messages covering all scenarios"""
        print("Generating test messages...")

        now = datetime.now()
        message_id = 1000  # Start from 1000 for test messages

        # Scenario 1: Messages from today (for "Today" filter)
        for hour in range(0, 24, 6):  # Every 6 hours
            for user in self.test_users:
                for group in self.test_groups[:2]:  # Only monitored groups
                    timestamp = int((now.replace(hour=hour, minute=random.randint(0, 59))).timestamp() * 1000)
                    self.cursor.execute("""
                        INSERT INTO messages (id, timestamp, group_id, sender_uuid, message_text, processed_at)
                        VALUES (?, ?, ?, ?, ?, datetime('now'))
                    """, (
                        message_id,
                        timestamp,
                        group["id"],
                        user["uuid"],
                        f"Today test message {hour:02d}:00 from {user['name']} in {group['name']}",

                    ))
                    self.message_scenarios.append({
                        "id": message_id,
                        "date": "today",
                        "group": group["id"],
                        "sender": user["uuid"],
                        "has_attachment": False
                    })
                    message_id += 1

        # Scenario 2: Messages from yesterday
        yesterday = now - timedelta(days=1)
        for hour in [9, 15, 21]:  # Specific hours
            for user in self.test_users[:2]:
                for group in self.test_groups:  # All groups
                    timestamp = int((yesterday.replace(hour=hour, minute=random.randint(0, 59))).timestamp() * 1000)
                    self.cursor.execute("""
                        INSERT INTO messages (id, timestamp, group_id, sender_uuid, message_text, processed_at)
                        VALUES (?, ?, ?, ?, ?, datetime('now'))
                    """, (
                        message_id,
                        timestamp,
                        group["id"],
                        user["uuid"],
                        f"Yesterday test message from {user['name']} in {group['name']}",
                    ))
                    self.message_scenarios.append({
                        "id": message_id,
                        "date": "yesterday",
                        "group": group["id"],
                        "sender": user["uuid"],
                        "has_attachment": False
                    })
                    message_id += 1

        # Scenario 3: Messages from last week (for date range testing)
        for days_ago in range(2, 8):
            past_date = now - timedelta(days=days_ago)
            timestamp = int((past_date.replace(hour=12, minute=0)).timestamp() * 1000)
            user = random.choice(self.test_users)
            group = random.choice(self.test_groups)

            self.cursor.execute("""
                INSERT INTO messages (id, timestamp, group_id, sender_uuid, message_text, processed_at)
                VALUES (?, ?, ?, ?, ?, datetime('now'))
            """, (
                message_id,
                timestamp,
                group["id"],
                user["uuid"],
                f"Past message from {days_ago} days ago",
            ))
            self.message_scenarios.append({
                "id": message_id,
                "date": f"{days_ago}_days_ago",
                "group": group["id"],
                "sender": user["uuid"],
                "has_attachment": False
            })
            message_id += 1

        # Scenario 4: Messages with attachments (mixed dates)
        attachment_messages = [
            {"days_ago": 0, "hour": 10, "type": "image"},
            {"days_ago": 0, "hour": 14, "type": "gif"},
            {"days_ago": 1, "hour": 16, "type": "sticker"},
            {"days_ago": 3, "hour": 11, "type": "document"},
        ]

        for msg_data in attachment_messages:
            msg_date = now - timedelta(days=msg_data["days_ago"])
            timestamp = int((msg_date.replace(hour=msg_data["hour"], minute=30)).timestamp() * 1000)
            user = random.choice(self.test_users)
            group = random.choice(self.test_groups[:2])  # Only monitored

            # Insert message
            self.cursor.execute("""
                INSERT INTO messages (id, timestamp, group_id, sender_uuid, message_text, processed_at)
                VALUES (?, ?, ?, ?, ?, datetime('now'))
            """, (
                message_id,
                timestamp,
                group["id"],
                user["uuid"],
                f"Message with {msg_data['type']} attachment",
            ))

            # Insert attachment
            self.cursor.execute("""
                INSERT INTO attachments (message_id, attachment_id, filename, content_type, file_size)
                VALUES (?, ?, ?, ?, ?)
            """, (
                message_id,
                f"ATTACH_{message_id}",
                f"test_{msg_data['type']}.{msg_data['type'][:3]}",
                f"{msg_data['type']}/test",
                random.randint(1000, 50000)
            ))

            self.message_scenarios.append({
                "id": message_id,
                "date": "today" if msg_data["days_ago"] == 0 else f"{msg_data['days_ago']}_days_ago",
                "group": group["id"],
                "sender": user["uuid"],
                "has_attachment": True,
                "attachment_type": msg_data["type"]
            })
            message_id += 1

        # Scenario 5: Messages in different time ranges (for hours filter)
        time_ranges = [
            {"hours": 1, "count": 3},
            {"hours": 3, "count": 5},
            {"hours": 6, "count": 8},
            {"hours": 12, "count": 10},
            {"hours": 24, "count": 15},
        ]

        for time_range in time_ranges:
            cutoff_time = now - timedelta(hours=time_range["hours"])
            for i in range(time_range["count"]):
                # Distribute messages within the time range
                offset_minutes = random.randint(0, time_range["hours"] * 60)
                msg_time = cutoff_time + timedelta(minutes=offset_minutes)
                timestamp = int(msg_time.timestamp() * 1000)

                user = random.choice(self.test_users)
                group = random.choice(self.test_groups[:2])

                self.cursor.execute("""
                    INSERT INTO messages (id, timestamp, group_id, sender_uuid, message_text, processed_at)
                    VALUES (?, ?, ?, ?, ?, datetime('now'))
                """, (
                    message_id,
                    timestamp,
                    group["id"],
                    user["uuid"],
                    f"Message within {time_range['hours']} hours",
                ))

                self.message_scenarios.append({
                    "id": message_id,
                    "hours_ago": time_range["hours"],
                    "group": group["id"],
                    "sender": user["uuid"],
                    "has_attachment": False
                })
                message_id += 1

        self.conn.commit()
        print(f"Generated {message_id - 1000} test messages covering all scenarios.")

    def create_test_data_report(self):
        """Create a report of test data created"""
        print("\n" + "="*60)
        print("TEST DATA CREATION REPORT")
        print("="*60)

        # Count messages by group
        print("\nMessages by Group:")
        for group in self.test_groups:
            self.cursor.execute("SELECT COUNT(*) as count FROM messages WHERE group_id = ?", (group["id"],))
            count = self.cursor.fetchone()["count"]
            monitored = "✓" if group["monitored"] else "✗"
            print(f"  {group['name']} (Monitored: {monitored}): {count} messages")

        # Count messages by user
        print("\nMessages by User:")
        for user in self.test_users:
            self.cursor.execute("SELECT COUNT(*) as count FROM messages WHERE sender_uuid = ?", (user["uuid"],))
            count = self.cursor.fetchone()["count"]
            print(f"  {user['name']}: {count} messages")

        # Count messages by date
        print("\nMessages by Date:")
        self.cursor.execute("""
            SELECT DATE(datetime(timestamp/1000, 'unixepoch', 'localtime')) as date, COUNT(*) as count
            FROM messages
            WHERE group_id LIKE 'TEST_GROUP_%'
            GROUP BY date
            ORDER BY date DESC
        """)
        for row in self.cursor.fetchall():
            print(f"  {row['date']}: {row['count']} messages")

        # Count messages with attachments
        self.cursor.execute("""
            SELECT COUNT(DISTINCT m.id) as count
            FROM messages m
            JOIN attachments a ON m.id = a.message_id
            WHERE m.group_id LIKE 'TEST_GROUP_%'
        """)
        attachment_count = self.cursor.fetchone()["count"]
        print(f"\nMessages with attachments: {attachment_count}")

        # Save scenarios to file for testing
        with open("test_scenarios.json", "w") as f:
            import json
            json.dump({
                "groups": self.test_groups,
                "users": self.test_users,
                "total_messages": len(self.message_scenarios),
                "scenarios": self.message_scenarios[:10]  # Sample scenarios
            }, f, indent=2)

        print("\nTest scenarios saved to test_scenarios.json")
        print("="*60)

    def run(self):
        """Run the complete test data generation"""
        try:
            self.clean_test_data()
            self.create_test_groups_and_users()
            self.generate_test_messages()
            self.create_test_data_report()
            print("\n✅ Test data generation complete!")
        except Exception as e:
            print(f"❌ Error generating test data: {e}")
            self.conn.rollback()
        finally:
            self.conn.close()

if __name__ == "__main__":
    generator = TestDataGenerator()
    generator.run()