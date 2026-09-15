import base64

from email.mime.text import MIMEText

from langchain_core.tools import tool
from langgraph.types import interrupt

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.auth.exceptions import RefreshError

from google_auth_helpers import (
    build_auth_required,
    get_google_credentials,
    is_auth_failure,
)


def _gmail_service(
    user_id: str,
    thread_id: str | None = None,
):

    creds, auth_info = get_google_credentials(
        user_id=user_id,
        service="Gmail",
        thread_id=thread_id,
    )

    if auth_info:
        interrupt(auth_info)

    if creds is None:
        interrupt(
            build_auth_required(
                user_id=user_id,
                service="Gmail",
                thread_id=thread_id,
            )
        )

    return build(
        "gmail",
        "v1",
        credentials=creds,
    )


def _create_message(
    to_email: str,
    subject: str,
    body: str,
):

    message = MIMEText(body)

    message["To"] = to_email
    message["Subject"] = subject

    encoded_message = base64.urlsafe_b64encode(
        message.as_bytes()
    ).decode()

    return {
        "raw": encoded_message
    }


@tool
def _send_email(
    user_id: str,
    to_email: str,
    subject: str,
    body: str,
    thread_id: str | None = None,
) -> str:
    """
    Sends an email using the user's connected Gmail account.

    Args:
        user_id: The authenticated application user ID.
        to_email: Recipient email address.
        subject: Email subject.
        body: Email body.
    """

    service = _gmail_service(
        user_id=user_id,
        thread_id=thread_id,
    )

    try:

        message = _create_message(
            to_email=to_email,
            subject=subject,
            body=body,
        )

        result = (
            service
            .users()
            .messages()
            .send(
                userId="me",
                body=message,
            )
            .execute()
        )

        return (
            f"Email successfully sent to "
            f"{to_email}."
        )

    except RefreshError as e:

        print(
            f"[GMAIL AUTH] RefreshError "
            f"for {user_id}: {repr(e)}"
        )

        interrupt(
            build_auth_required(
                user_id=user_id,
                service="Gmail",
                thread_id=thread_id,
                revoke=True,
            )
        )

    except HttpError as e:

        print(
            f"[GMAIL] HttpError "
            f"for {user_id}: {repr(e)}"
        )

        if is_auth_failure(e):

            interrupt(
                build_auth_required(
                    user_id=user_id,
                    service="Gmail",
                    thread_id=thread_id,
                    revoke=True,
                )
            )

        return f"Gmail send failed: {e}"

    except Exception as e:

        print(
            f"[GMAIL] Unexpected error: "
            f"{repr(e)}"
        )

        return f"Failed to send email: {e}"

@tool
def send_email_tool(
    to_email: str,
    subject: str,
    body: str,
) -> str:
    """
    Sends an email using the authenticated user's Gmail account.

    The backend supplies the authenticated user.
    """

    raise RuntimeError(
        "send_email_tool must be executed through the backend."
    )