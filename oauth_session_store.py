import time


SESSION_TTL_SECONDS = 600

_sessions = {}


def save_session(
    state: str,
    data: dict,
):
    _sessions[state] = {
        **data,
        "created_at": time.time(),
    }


def get_session(
    state: str,
):
    session = _sessions.get(state)

    if not session:
        return None

    if (
        time.time() - session["created_at"]
        > SESSION_TTL_SECONDS
    ):
        _sessions.pop(state, None)
        return None

    return session


def delete_session(
    state: str,
):
    _sessions.pop(state, None)
