"""Process-local runtime state for waiting authorization requests."""

from app.authorization.requests import AuthorizationRequestManager


_requests = AuthorizationRequestManager()


def get_authorization_request_manager() -> AuthorizationRequestManager:
    """Return the process-local authorization waiting room."""
    return _requests
