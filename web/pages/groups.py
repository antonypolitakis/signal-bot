"""
Groups Management Page for Signal Bot Web Interface

PURPOSE:
    Manages Signal group configurations and monitoring settings for the bot system.
    Controls which groups the bot monitors and processes messages from.

FUNCTIONALITY:
    1. Group Monitoring:
       - Display monitored and unmonitored Signal groups
       - Toggle group monitoring status
       - Show group member information and counts

    2. Group Statistics:
       - Display message counts per group
       - Show member lists with UUID and phone numbers
       - Track group activity levels

    3. Group Actions:
       - Enable/disable monitoring for specific groups
       - View group messages (redirects to messages page)
       - Refresh group member lists from Signal

PAGE STRUCTURE:
    - Tab interface (Monitored Groups / Unmonitored Groups)
    - Group cards/tables with monitoring controls
    - Member details expandable sections
    - Quick action buttons for group management

TESTING:
    1. Navigate to /groups endpoint
    2. Verify all groups display correctly
    3. Test monitoring/unmonitoring group toggle
    4. Verify member lists show correct UUID and phone information
    5. Test "View Messages" link navigation
    6. Check tab switching functionality
    7. Verify group counts and statistics accuracy

API ENDPOINTS USED:
    - POST /api/groups/monitor - Enable group monitoring
    - POST /api/groups/unmonitor - Disable group monitoring
    - GET /api/groups/refresh - Refresh group member lists

DATABASE INTERACTIONS:
    - Reads from groups table for group configurations
    - Updates groups.is_monitored field for monitoring status
    - Joins with messages table for statistics
    - Reads group_members for member information
"""

from typing import Dict, Any
from ..shared.base_page import BasePage


class GroupsPage(BasePage):
    @property
    def title(self) -> str:
        return "👥 Groups Management"

    @property
    def nav_key(self) -> str:
        return "groups"

    @property
    def subtitle(self) -> str:
        return "Configure which groups the bot should monitor"

    def get_custom_css(self) -> str:
        """No custom CSS - using shared styling."""
        return ""

    def get_custom_js(self) -> str:
        return """
            // Tab switching is now handled by common.js

            const toggleGroupMonitoring = debounce(async function(groupId, monitor) {
                const btn = event.target;
                setButtonLoading(btn, true, '⏳ Updating...');

                try {
                    const payload = {group_id: groupId, is_monitored: monitor};

                    const response = await fetchWithTimeout('/api/groups/monitor', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify(payload)
                    }, 10000);

                    if (response.ok) {
                        location.reload();
                    } else {
                        const errorText = await response.text();
                        showNotification('Failed to update group monitoring: ' + errorText, 'error');
                        setButtonLoading(btn, false);
                    }
                } catch (error) {
                    showNotification('Error: ' + error.message, 'error');
                    setButtonLoading(btn, false);
                }
            }, 300);
        """

    def render_content(self, query: Dict[str, Any]) -> str:
        tab = query.get('tab', ['monitored'])[0]

        # Get stats for tab labels - filter out groups with 0 members and test groups
        all_groups = self.db.get_all_groups()
        # Filter out groups with 0 members and test groups
        all_groups = [g for g in all_groups if g.member_count > 0 and not (g.group_name and 'test' in g.group_name.lower())]
        monitored_count = len([g for g in all_groups if g.is_monitored])
        unmonitored_count = len([g for g in all_groups if not g.is_monitored])

        return f"""
            <div class="user-tabs">
                <a href="/groups?tab=monitored" class="tab-btn {'active' if tab == 'monitored' else ''}">Monitored Groups ({monitored_count})</a>
                <a href="/groups?tab=unmonitored" class="tab-btn {'active' if tab == 'unmonitored' else ''}">Unmonitored Groups ({unmonitored_count})</a>
            </div>

            <div id="{tab}-tab" class="tab-content active">
                {self._render_monitored_tab() if tab == 'monitored' else self._render_unmonitored_tab()}
            </div>
        """

    def _render_monitored_tab(self) -> str:
        """Render the monitored groups tab content."""
        groups = [g for g in self.db.get_all_groups() if g.is_monitored and g.member_count > 0 and not (g.group_name and 'test' in g.group_name.lower())]

        if not groups:
            return """
                <div class="card">
                    <h3>Monitored Groups</h3>
                    <p class="text-muted">Groups that the bot is actively monitoring</p>
                    <div class="no-groups">No monitored groups found. Use the "Unmonitored Groups" tab to enable monitoring.</div>
                </div>
            """

        return f"""
            <div class="card">
                <h3>Monitored Groups</h3>
                <p class="text-muted">Groups that the bot is actively monitoring</p>
                {self._render_groups_table(groups, True)}
            </div>
        """

    def _render_unmonitored_tab(self) -> str:
        """Render the unmonitored groups tab content."""
        groups = [g for g in self.db.get_all_groups() if not g.is_monitored and g.member_count > 0 and not (g.group_name and 'test' in g.group_name.lower())]

        if not groups:
            return """
                <div class="card">
                    <h3>Unmonitored Groups</h3>
                    <p class="text-muted">Groups that are not being monitored by the bot</p>
                    <div class="no-groups">No unmonitored groups found. All discovered groups are being monitored.</div>
                </div>
            """

        return f"""
            <div class="card">
                <h3>Unmonitored Groups</h3>
                <p class="text-muted">Groups that are not being monitored by the bot</p>
                {self._render_groups_table(groups, False)}
            </div>
        """

    def _render_groups_table(self, groups, is_monitored: bool) -> str:
        """Render a table of groups."""
        from urllib.parse import quote

        rows_html = ""
        for group in groups:
            monitor_btn = "Unmonitor" if is_monitored else "Monitor"
            monitor_action = "false" if is_monitored else "true"

            # Get members for this group
            members = self.db.get_group_members(group.group_id)
            members_html = ""
            if members:
                member_details = []
                for member in members:
                    detail = self.format_user_display(member)
                    member_details.append(detail)
                members_html = "<br>".join(member_details)
            else:
                members_html = "No members"

            view_messages_btn = ""
            if is_monitored:
                view_messages_btn = f'<a href="/messages?tab=all&group_id={quote(group.group_id)}" class="btn">View Messages</a>'

            # Escape the group ID for JavaScript
            escaped_group_id = group.group_id.replace("'", "\\'").replace('"', '\\"')

            rows_html += f"""
            <tr>
                <td><strong>{group.group_name or 'Unnamed Group'}</strong></td>
                <td>{group.group_id}</td>
                <td>{group.member_count}</td>
                <td style="max-width: 300px; word-wrap: break-word;">{members_html}</td>
                <td style="white-space: nowrap;">
                    <button class="btn" onclick="toggleGroupMonitoring('{escaped_group_id}', {monitor_action})">
                        {monitor_btn}
                    </button>
                    {view_messages_btn}
                </td>
            </tr>
            """

        return f"""
            <table>
                <thead>
                    <tr>
                        <th>Group Name</th>
                        <th>Group ID</th>
                        <th>Members</th>
                        <th>Member Details</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
                    {rows_html if rows_html else '<tr><td colspan="5" class="text-center text-muted">No groups found</td></tr>'}
                </tbody>
            </table>
        """