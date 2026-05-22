from langchain_core.tools import tool
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from datetime import datetime, timedelta
import uuid

from google_auth_flow import (
    credentials_from_token_dict,
    get_auth_url
)
from token_store import get_token, save_token
from drive_tools import AUTH_REQUIRED_PREFIX


def _calendar_service(user_email: str):
    """
    Returns authenticated Google Calendar service.
    """

    token_dict = get_token(user_email)

    if not token_dict:
        return None
    
    creds = credentials_from_token_dict(token_dict)

    save_token(user_email, {
        "token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
        "scopes": list(creds.scopes or []),
        "expiry": creds.expiry.isoformat() if creds.expiry else None,
    })

    return build("calendar", "v3", credentials=creds)





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

    if service is None:
        auth_url = get_auth_url(state=user_email)

        return (
            f"{AUTH_REQUIRED_PREFIX}{auth_url}\n"
            f"User {user_email} is not authenticated with Google Calendar. "
            f"They must visit the URL above to grant access."
        )

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
        return f"Google Calendar API error: {str(e)}"

    except Exception as e:
        return f"Failed to create calendar invite: {str(e)}"
