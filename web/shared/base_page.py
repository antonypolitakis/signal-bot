"""
Base page class for Signal Bot web interface.

Provides consistent structure and functionality for all pages.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from urllib.parse import parse_qs

from models.database import DatabaseManager
from services.setup import SetupService
from .templates import render_page, get_standard_date_selector


class BasePage(ABC):
    """Base class for all web pages."""

    def __init__(self, db: DatabaseManager, setup_service: SetupService, ai_provider=None):
        self.db = db
        self.setup_service = setup_service
        self.ai_provider = ai_provider
        # AI analysis services are handled by AIAnalysisService
        self.sentiment_analyzer = None
        self.summarizer = None

    @property
    @abstractmethod
    def title(self) -> str:
        """Page title."""
        pass

    @property
    @abstractmethod
    def nav_key(self) -> str:
        """Navigation key for highlighting active nav item."""
        pass

    @property
    @abstractmethod
    def subtitle(self) -> str:
        """Page subtitle."""
        pass

    @abstractmethod
    def render_content(self, query: Dict[str, Any]) -> str:
        """Render the main content of the page."""
        pass

    def get_custom_css(self) -> str:
        """Override to provide page-specific CSS."""
        return ""

    def get_custom_js(self) -> str:
        """Override to provide page-specific JavaScript."""
        return ""

    def render(self, query: Dict[str, Any]) -> str:
        """Render the complete page."""
        content = self.render_content(query)
        return render_page(
            title=self.title,
            subtitle=self.subtitle,
            content=content,
            active_page=self.nav_key,
            extra_css=self.get_custom_css(),
            extra_js=self.get_custom_js()
        )

    def parse_query_string(self, query_string: str) -> Dict[str, Any]:
        """Parse query string into dictionary."""
        return parse_qs(query_string) if query_string else {}

    def get_user_timezone(self, query: Dict[str, Any]) -> Optional[str]:
        """Get user timezone from database preferences."""
        # Import here to avoid circular dependency
        from services.user_preferences import UserPreferencesService

        # Get from database preferences
        prefs_service = UserPreferencesService(self.db)
        return prefs_service.get_timezone()

    def format_user_display(self, user) -> str:
        """Format user display name consistently - prioritize real friendly names, then phone, then UUID."""
        # Handle None user
        if user is None:
            return '<strong>Unknown User</strong><br><small class="text-muted">User not found</small>'

        # Check if friendly name exists and is not the generic fallback
        if (user.friendly_name and
            user.friendly_name != f"User {user.phone_number}" and
            user.friendly_name != f"User {user.uuid}"):
            # Real friendly name exists - use it with phone/UUID in parentheses
            if user.phone_number:
                return f'<strong>{user.friendly_name}</strong><br><small class="text-muted">{user.phone_number}</small>'
            else:
                return f'<strong>{user.friendly_name}</strong><br><small class="text-muted">UUID: {user.uuid}</small>'
        elif user.phone_number:
            # No real friendly name, show phone number
            return f'<strong>{user.phone_number}</strong><br><small class="text-muted">UUID: {user.uuid}</small>'
        elif hasattr(user, 'display_name') and user.display_name:
            # No friendly name or phone, show display name with UUID
            return f'<strong>{user.display_name}</strong><br><small class="text-muted">UUID: {user.uuid}</small>'
        else:
            # Only UUID available
            return f'<strong>UUID: {user.uuid}</strong><br><small class="text-muted">No phone number</small>'

    def get_standard_date_selector(self, input_id: str = "date-input", **kwargs) -> str:
        """Get standardized date selector."""
        return get_standard_date_selector(input_id=input_id, **kwargs)

    def format_timestamp(self, timestamp_ms: Optional[int], user_timezone: Optional[str] = None, include_time: bool = True) -> str:
        """Format timestamp for display using user timezone and preferences."""
        if not timestamp_ms:
            return "Unknown time"

        try:
            from datetime import datetime, timezone
            import pytz
            from services.user_preferences import UserPreferencesService

            # Get user preferences
            prefs_service = UserPreferencesService(self.db)

            # Convert milliseconds to datetime
            dt = datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc)

            # Convert to user timezone
            if not user_timezone:
                user_timezone = prefs_service.get_timezone()

            try:
                user_tz = pytz.timezone(user_timezone)
                dt = dt.astimezone(user_tz)
            except Exception:
                pass  # Fall back to UTC if timezone is invalid

            # Format using user preferences
            return prefs_service.format_date(dt, include_time=include_time)
        except Exception:
            return "Unknown time"

    def get_today_in_user_timezone(self) -> tuple:
        """Get today's date range in user's timezone.
        Returns (start_of_day_ms, end_of_day_ms, iso_date_string, formatted_date_string)
        """
        from datetime import datetime
        import pytz
        from services.user_preferences import UserPreferencesService

        prefs_service = UserPreferencesService(self.db)
        user_timezone = prefs_service.get_timezone()

        try:
            tz = pytz.timezone(user_timezone)
            now = datetime.now(tz)
            start_of_today = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end_of_today = now.replace(hour=23, minute=59, second=59, microsecond=999999)

            start_ms = int(start_of_today.timestamp() * 1000)
            end_ms = int(end_of_today.timestamp() * 1000)
            iso_date_string = now.strftime('%Y-%m-%d')  # Always ISO for database
            formatted_date_string = prefs_service.format_date(now, include_time=False)  # User preference for display

            return (start_ms, end_ms, iso_date_string, formatted_date_string)
        except Exception:
            # Fallback to UTC
            now = datetime.utcnow()
            start_of_today = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end_of_today = now.replace(hour=23, minute=59, second=59, microsecond=999999)

            start_ms = int(start_of_today.timestamp() * 1000)
            end_ms = int(end_of_today.timestamp() * 1000)
            iso_date_string = now.strftime('%Y-%m-%d')
            formatted_date_string = iso_date_string  # Fallback uses ISO for both

            return (start_ms, end_ms, iso_date_string, formatted_date_string)