"""
User Preferences Service for Signal Bot

This module handles all user preference settings stored in the database,
including timezone, date/time formats, and UI preferences.
"""

import json
from typing import Any, Dict, Optional
from datetime import datetime
import pytz
from models.database import DatabaseManager

class UserPreferencesService:
    """Service for managing user preferences."""

    # Default preferences when none are set
    DEFAULT_PREFERENCES = {
        'timezone': 'UTC',  # Default to UTC for consistency
        'date_format': 'YYYY-MM-DD',  # ISO format
        'time_format': '24h',  # 24-hour format
        'messages_per_page': 50,
        'auto_refresh_interval': 30,  # seconds, 0 = disabled
        'show_message_previews': True,
        'show_reaction_notifications': True,
        'enable_auto_reactions': True,
        'default_emoji_mode': 'random',  # random, fixed, or disabled
        'language': 'en',  # for future internationalization
        'show_unmonitored_groups': False,
        'compact_message_view': False,
        'enable_ai_features': True,
        'default_ai_provider': 'ollama',
        'activity_chart_style': 'bars',  # bars or heatmap
        'dashboard_refresh_rate': 60,  # seconds
        'filter_persist_navigation': True,  # Keep filters when navigating
        'show_deleted_messages': False,
        'notification_sound': True,
    }

    # Available options for dropdown preferences
    PREFERENCE_OPTIONS = {
        'timezone': None,  # Will be populated with pytz timezones
        'date_format': [
            'YYYY-MM-DD',  # ISO format (2024-12-25)
            'DD/MM/YYYY',  # European format (25/12/2024)
            'MM/DD/YYYY',  # American format (12/25/2024)
            'DD.MM.YYYY',  # German format (25.12.2024)
            'YYYY年MM月DD日',  # Japanese format
        ],
        'time_format': ['24h', '12h'],
        'messages_per_page': [25, 50, 100, 200],
        'auto_refresh_interval': [0, 15, 30, 60, 120, 300],  # seconds
        'default_emoji_mode': ['random', 'fixed', 'disabled'],
        'language': ['en', 'ja', 'es', 'fr', 'de', 'zh'],
        'default_ai_provider': ['ollama', 'openai', 'anthropic', 'gemini', 'groq'],
        'activity_chart_style': ['bars', 'heatmap', 'line'],
        'dashboard_refresh_rate': [0, 30, 60, 120, 300],
    }

    def __init__(self, db: DatabaseManager):
        """Initialize the preferences service."""
        self.db = db
        self._preferences_cache = None
        self._cache_timestamp = None
        self._cache_timeout = 60  # Cache for 60 seconds

        # Populate timezone options
        self.PREFERENCE_OPTIONS['timezone'] = self._get_timezone_options()

    def _get_timezone_options(self) -> list:
        """Get list of all available timezones grouped by region."""
        # Get all timezones and group them
        timezones = []

        # Common timezones first
        common_zones = [
            'UTC',
            'US/Eastern',
            'US/Central',
            'US/Mountain',
            'US/Pacific',
            'Europe/London',
            'Europe/Paris',
            'Europe/Berlin',
            'Asia/Tokyo',
            'Asia/Shanghai',
            'Asia/Hong_Kong',
            'Asia/Singapore',
            'Australia/Sydney',
            'Australia/Melbourne',
        ]

        timezones.extend(common_zones)

        # Add all pytz timezones (excluding the common ones already added)
        all_zones = [tz for tz in pytz.all_timezones if tz not in common_zones]
        timezones.extend(sorted(all_zones))

        return timezones

    def get_all_preferences(self) -> Dict[str, Any]:
        """Get all user preferences from database or cache."""
        # Check cache first
        if self._preferences_cache and self._cache_timestamp:
            if (datetime.now() - self._cache_timestamp).seconds < self._cache_timeout:
                return self._preferences_cache

        # Load from database
        preferences = self.DEFAULT_PREFERENCES.copy()

        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT key, value FROM bot_config
                WHERE key LIKE 'pref_%'
            """)

            for row in cursor.fetchall():
                key = row['key'].replace('pref_', '')
                try:
                    # Try to parse as JSON for complex values
                    value = json.loads(row['value'])
                except (json.JSONDecodeError, TypeError):
                    # If not JSON, use as string
                    value = row['value']

                # Convert string booleans
                if value in ('true', 'True'):
                    value = True
                elif value in ('false', 'False'):
                    value = False

                # Convert string numbers
                try:
                    if key in ['messages_per_page', 'auto_refresh_interval',
                              'dashboard_refresh_rate']:
                        value = int(value)
                except (ValueError, TypeError):
                    pass

                preferences[key] = value

        # Update cache
        self._preferences_cache = preferences
        self._cache_timestamp = datetime.now()

        return preferences

    def get_preference(self, key: str) -> Any:
        """Get a specific preference value."""
        preferences = self.get_all_preferences()
        return preferences.get(key, self.DEFAULT_PREFERENCES.get(key))

    def set_preference(self, key: str, value: Any) -> bool:
        """Set a preference value in the database."""
        # Validate the preference key
        if key not in self.DEFAULT_PREFERENCES:
            raise ValueError(f"Unknown preference key: {key}")

        # Validate the value if options are defined
        if key in self.PREFERENCE_OPTIONS and self.PREFERENCE_OPTIONS[key]:
            if value not in self.PREFERENCE_OPTIONS[key]:
                raise ValueError(f"Invalid value for {key}: {value}")

        # Convert value to string for storage
        if isinstance(value, bool):
            value_str = 'true' if value else 'false'
        elif isinstance(value, (dict, list)):
            value_str = json.dumps(value)
        else:
            value_str = str(value)

        # Store in database with 'pref_' prefix
        db_key = f'pref_{key}'

        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO bot_config (key, value, updated_at)
                VALUES (?, ?, datetime('now'))
            """, (db_key, value_str))

        # Clear cache
        self._preferences_cache = None

        return True

    def set_multiple_preferences(self, preferences: Dict[str, Any]) -> bool:
        """Set multiple preferences at once."""
        for key, value in preferences.items():
            self.set_preference(key, value)
        return True

    def reset_to_defaults(self) -> bool:
        """Reset all preferences to default values."""
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            # Delete all preference entries
            cursor.execute("DELETE FROM bot_config WHERE key LIKE 'pref_%'")

        # Clear cache
        self._preferences_cache = None

        return True

    def get_timezone(self) -> str:
        """Get the configured timezone."""
        return self.get_preference('timezone')

    def get_date_format(self) -> str:
        """Get the configured date format."""
        return self.get_preference('date_format')

    def get_time_format(self) -> str:
        """Get the configured time format."""
        return self.get_preference('time_format')

    def format_date(self, dt: datetime, include_time: bool = False) -> str:
        """Format a datetime according to user preferences."""
        date_format = self.get_date_format()
        time_format = self.get_time_format()

        # Convert date format to Python strftime format
        format_map = {
            'YYYY-MM-DD': '%Y-%m-%d',
            'DD/MM/YYYY': '%d/%m/%Y',
            'MM/DD/YYYY': '%m/%d/%Y',
            'DD.MM.YYYY': '%d.%m.%Y',
            'YYYY年MM月DD日': '%Y年%m月%d日',
        }

        date_fmt = format_map.get(date_format, '%Y-%m-%d')

        if include_time:
            if time_format == '12h':
                time_fmt = '%I:%M %p'
            else:
                time_fmt = '%H:%M'

            full_format = f"{date_fmt} {time_fmt}"
        else:
            full_format = date_fmt

        return dt.strftime(full_format)

    def convert_to_user_timezone(self, dt: datetime, from_tz: str = 'UTC') -> datetime:
        """Convert datetime to user's preferred timezone."""
        user_tz_name = self.get_timezone()

        # If datetime is naive, assume it's in from_tz
        if dt.tzinfo is None:
            from_timezone = pytz.timezone(from_tz)
            dt = from_timezone.localize(dt)

        # Convert to user timezone
        user_tz = pytz.timezone(user_tz_name)
        return dt.astimezone(user_tz)

    def export_preferences(self) -> Dict[str, Any]:
        """Export all preferences for backup."""
        return self.get_all_preferences()

    def import_preferences(self, preferences: Dict[str, Any]) -> bool:
        """Import preferences from backup."""
        return self.set_multiple_preferences(preferences)

    def get_preference_metadata(self) -> Dict[str, Dict]:
        """Get metadata about all preferences for UI generation."""
        metadata = {}

        for key, default_value in self.DEFAULT_PREFERENCES.items():
            metadata[key] = {
                'default': default_value,
                'current': self.get_preference(key),
                'type': type(default_value).__name__,
                'options': self.PREFERENCE_OPTIONS.get(key),
                'category': self._categorize_preference(key),
                'description': self._get_preference_description(key),
            }

        return metadata

    def _categorize_preference(self, key: str) -> str:
        """Categorize preference for UI grouping."""
        categories = {
            'Display': ['timezone', 'date_format', 'time_format', 'language'],
            'Messages': ['messages_per_page', 'show_message_previews', 'compact_message_view',
                        'show_deleted_messages', 'filter_persist_navigation'],
            'Notifications': ['show_reaction_notifications', 'notification_sound',
                             'auto_refresh_interval', 'dashboard_refresh_rate'],
            'AI & Automation': ['enable_ai_features', 'default_ai_provider',
                               'enable_auto_reactions', 'default_emoji_mode'],
            'Advanced': ['show_unmonitored_groups', 'activity_chart_style'],
        }

        for category, keys in categories.items():
            if key in keys:
                return category
        return 'Other'

    def _get_preference_description(self, key: str) -> str:
        """Get human-readable description for preference."""
        descriptions = {
            'timezone': 'Your local timezone for displaying dates and times',
            'date_format': 'How dates are displayed throughout the application',
            'time_format': '12-hour (AM/PM) or 24-hour time display',
            'messages_per_page': 'Number of messages to show per page',
            'auto_refresh_interval': 'How often to refresh data (0 = disabled)',
            'show_message_previews': 'Show message text previews in lists',
            'show_reaction_notifications': 'Display notifications for emoji reactions',
            'enable_auto_reactions': 'Automatically send emoji reactions to messages',
            'default_emoji_mode': 'How emojis are selected for auto-reactions',
            'language': 'Interface language',
            'show_unmonitored_groups': 'Display unmonitored groups in lists',
            'compact_message_view': 'Use compact spacing in message lists',
            'enable_ai_features': 'Enable AI-powered features',
            'default_ai_provider': 'Default AI provider for analysis',
            'activity_chart_style': 'Visual style for activity charts',
            'dashboard_refresh_rate': 'Dashboard auto-refresh interval (seconds)',
            'filter_persist_navigation': 'Keep filters when navigating between pages',
            'show_deleted_messages': 'Show deleted messages with strikethrough',
            'notification_sound': 'Play sound for new notifications',
        }

        return descriptions.get(key, f'Configure {key.replace("_", " ").title()}')