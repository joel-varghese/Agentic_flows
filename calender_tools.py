from langchain_core.tools import tool
from googleapiclient.discovery import build
from datetime import datetime, timedelta
import uuid

from google_auth_flow import credentials_from_token_dict
from token_store import load_token

@tool
def create_calender_event_tool(
    attendee_email: str,
    title: str,
    start_time: str,
    duration_minutes: int = 30,
    description: str = ""
) -> str:
    """
    Creates a Google Calendar event with a Google Meet link.

    Args:
        attendee_email: Email of invitee
        title: Meeting title
        start_time: ISO datetime format
        duration_minutes: Meeting duration
        description: Optional meeting description
    """

    try:
        token_dict = load_token()

        if not token_dict:
            return "User not authenticated with Google."
        
        creds = credentials_from_token_dict(token_dict)

        service = build("calender", "v3", credentials=creds)

        start_dt = datetime.fromisoformat(start_time)
        end_dt = start_dt + timedelta(minutes=duration_minutes)

        event = {
            "summary": title,
            "description": description,
            "start": {
                "dateTime": start_dt.isoformat(),
                "timeZone": "UTC",
            },
            "end": {
                "dateTime": end_dt.isoformat(),
                "timeZone": "UTC",
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
            calenderId="primary",
            body=event,
            conferenceDataVersion=1,
            sendUpdates="all"
        ).execute()

        meet_link = created_event.get(
            "hangoutLink",
            "No Meet link generated."            
        )

        return (
            f"Calendar invite created successfully.\n"
            f"Google Meet Link: {meet_link}"
        )
    
    except Exception as e:
        return f"Failed to create calendar invite: {str(e)}"
