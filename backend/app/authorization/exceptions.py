"""Domain errors for authorization decisions."""


class PermissionDenied(Exception):
    """Raised when a principal cannot request a permission."""


class AbortException(Exception):
    """Raised when the user aborts the current agent operation."""


class AuthorizationTimeout(Exception):
    """Raised when no authorization decision arrives in time."""
