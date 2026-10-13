"""Only deliberately sanitized backup diagnostics may enter the public catalogue."""


class BackupIntegrityError(ValueError):
    """Safe, application-authored message (never raw driver or subprocess stderr)."""
