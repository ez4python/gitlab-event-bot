class GitLabEventParser:
    @staticmethod
    def parse_push_event(event_data):
        """Parse a GitLab push event."""
        project_name = event_data.get('project', {}).get('name', 'Unknown Project')
        user_name = event_data.get('user_name', 'Unknown User')
        ref = event_data.get('ref', '').replace('refs/heads/', '')
        commits = event_data.get('commits', [])

        message = f"🔄 <b>Push Event</b>\n"
        message += f"<b>Project:</b> {project_name}\n"
        message += f"<b>Branch:</b> {ref}\n"
        message += f"<b>By:</b> {user_name}\n\n"

        if commits:
            message += "<b>Commits:</b>\n"
            for commit in commits[:5]:  # Limit to 5 commits to avoid message too long
                commit_id = commit.get('id', '')[:8]
                commit_message = commit.get('message', '').split('\n')[0]
                message += f"• <code>{commit_id}</code>: {commit_message}\n"

            if len(commits) > 5:
                message += f"... and {len(commits) - 5} more commits\n"

        return message

    @staticmethod
    def parse_merge_request_event(event_data):
        """Parse a GitLab merge request event."""
        project_name = event_data.get('project', {}).get('name', 'Unknown Project')
        user_name = event_data.get('user', {}).get('name', 'Unknown User')
        mr = event_data.get('object_attributes', {})
        action = mr.get('action', 'unknown')
        title = mr.get('title', 'Unknown Title')
        source_branch = mr.get('source_branch', 'unknown')
        target_branch = mr.get('target_branch', 'unknown')
        url = mr.get('url', '#')

        message = f"🔀 <b>Merge Request: {action}</b>\n"
        message += f"<b>Project:</b> {project_name}\n"
        message += f"<b>Title:</b> {title}\n"
        message += f"<b>By:</b> {user_name}\n"
        message += f"<b>Source:</b> {source_branch} → <b>Target:</b> {target_branch}\n"
        message += f"<b>URL:</b> <a href='{url}'>{url}</a>\n"

        return message

    @staticmethod
    def parse_issue_event(event_data):
        """Parse a GitLab issue event."""
        project_name = event_data.get('project', {}).get('name', 'Unknown Project')
        user_name = event_data.get('user', {}).get('name', 'Unknown User')
        issue = event_data.get('object_attributes', {})
        action = issue.get('action', 'unknown')
        title = issue.get('title', 'Unknown Title')
        url = issue.get('url', '#')

        message = f"🐞 <b>Issue: {action}</b>\n"
        message += f"<b>Project:</b> {project_name}\n"
        message += f"<b>Title:</b> {title}\n"
        message += f"<b>By:</b> {user_name}\n"
        message += f"<b>URL:</b> <a href='{url}'>{url}</a>\n"

        return message

    @staticmethod
    def parse_comment_event(event_data):
        """Parse a GitLab comment event."""
        project_name = event_data.get('project', {}).get('name', 'Unknown Project')
        user_name = event_data.get('user', {}).get('name', 'Unknown User')
        comment = event_data.get('object_attributes', {})
        note = comment.get('note', 'No content')
        url = comment.get('url', '#')

        # Determine what the comment is on
        noteable_type = comment.get('noteable_type', 'Unknown')

        message = f"💬 <b>New Comment on {noteable_type}</b>\n"
        message += f"<b>Project:</b> {project_name}\n"
        message += f"<b>By:</b> {user_name}\n"
        message += f"<b>Comment:</b> {note[:100]}{'...' if len(note) > 100 else ''}\n"
        message += f"<b>URL:</b> <a href='{url}'>{url}</a>\n"

        return message

    @staticmethod
    def parse_pipeline_event(event_data):
        """Parse a GitLab pipeline event."""
        project_name = event_data.get('project', {}).get('name', 'Unknown Project')
        user_name = event_data.get('user', {}).get('name', 'Unknown User')
        pipeline = event_data.get('object_attributes', {})
        status = pipeline.get('status', 'unknown')
        ref = pipeline.get('ref', 'unknown')
        url = pipeline.get('url', '#')

        # Emoji based on status
        status_emoji = {
            'success': '✅',
            'failed': '❌',
            'running': '🏃',
            'pending': '⏳',
            'canceled': '🚫',
            'skipped': '⏭️'
        }.get(status, '❓')

        message = f"{status_emoji} <b>Pipeline: {status}</b>\n"
        message += f"<b>Project:</b> {project_name}\n"
        message += f"<b>Branch:</b> {ref}\n"
        message += f"<b>By:</b> {user_name}\n"
        message += f"<b>URL:</b> <a href='{url}'>{url}</a>\n"

        return message

    @staticmethod
    def parse_event(event_type, event_data):
        """Parse a GitLab event based on its type."""
        parsers = {
            'push': GitLabEventParser.parse_push_event,
            'merge_request': GitLabEventParser.parse_merge_request_event,
            'issue': GitLabEventParser.parse_issue_event,
            'note': GitLabEventParser.parse_comment_event,
            'pipeline': GitLabEventParser.parse_pipeline_event,
        }

        parser = parsers.get(event_type)
        if parser:
            return parser(event_data)

        # Default parser for unknown event types
        return f"📣 <b>GitLab Event: {event_type}</b>\n" + \
            f"Received a GitLab event of type '{event_type}'. " + \
            "No specific parser available for this event type."
