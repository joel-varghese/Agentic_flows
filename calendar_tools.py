from langchain_core.tools import tool
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from langgraph.types import interrupt

from datetime import datetime, timedelta
import uuid

from google_auth_helpers import (
    get_google_credentials,
    is_auth_failure,
    auth_required_interrupt
)


def _calendar_service(user_email: str):
    """
    Returns a Google Calendar service.

    If authentication is required, pauses the LangGraph execution
    using interrupt().
    """
    creds, auth_msg = get_google_credentials(user_email)
    if auth_msg:
        interrupt(auth_msg)
    if creds is None:
        auth_required_interrupt(
            user_email,
            "Google Calendar",
        )

    return build("calendar", "v3", credentials=creds), None


@tool
def create_calendar_event_tool(
    user_email: str,
    attendee_email: str,
    title: str,
    start_time: str,
    duration_minutes: int = 30,
    description: str = "",
    timezone: str = "UTC",
) -> str:
    """
    Creates a Google Calendar event with a Google Meet link.

    Args:
        user_email: Email of authenticated Google user
        attendee_email: Recipient invited to the meeting
        title: Meeting title
        start_time: ISO datetime format
            Example:
            2026-05-25T15:00:00
        duration_minutes: Meeting duration
        description: Optional meeting description
        timezone: Timezone string
            Example: America/New_York
    """

    service = _calendar_service(user_email)

    try:
        start_dt = datetime.fromisoformat(start_time)
        end_dt = start_dt + timedelta(minutes=duration_minutes)

        event = {
            "summary": title,
            "description": description,
            "start": {
                "dateTime": start_dt.isoformat(),
                "timeZone": timezone,
            },
            "end": {
                "dateTime": end_dt.isoformat(),
                "timeZone": timezone,
            },
            "attendees": [
                {"email": attendee_email}
            ],
            "conferenceData": {
                "createRequest": {
                    "requestId": str(uuid.uuid4()),
                    "conferenceSolutionKey": {
                        "type": "hangoutsMeet"
                    }
                }
            }
        }

        created_event = service.events().insert(
            calendarId="primary",
            body=event,
            conferenceDataVersion=1,
            sendUpdates="all"
        ).execute()

        meet_link = created_event.get(
            "hangoutLink",
            "No Meet link generated."
        )

        html_link = created_event.get(
            "htmlLink",
            "No calendar link available"
        )

        return (
            f"Calendar invite created successfully.\n\n"
            f"Event: {title}\n"
            f"Attendee: {attendee_email}\n"
            f"Start: {start_dt.isoformat()} ({timezone})\n"
            f"Duration: {duration_minutes} minutes\n\n"
            f"Google Meet: {meet_link}\n"
            f"Calendar Event: {html_link}"
        )

    except HttpError as e:

        print(
            f"[CALENDAR] HttpError for {user_email}: "
            f"{repr(e)}"
        )
                
        if is_auth_failure(e):
            _, auth_info = get_google_credentials(user_email)

            if auth_info:
                interrupt(auth_info)

            auth_required_interrupt(
                user_email,
                "Google Calendar"
            )

            return f"Google Calendar API error: {str(e)}"

    except Exception as e:
        if is_auth_failure(e):
            _, auth_info = get_google_credentials(
                user_email
            )

            if auth_info:
                interrupt(auth_info)

            auth_required_interrupt(
                user_email,
                "Google Calendar",
            )

        return (
            f"Failed to create calendar invite: "
            f"{str(e)}"
        )
