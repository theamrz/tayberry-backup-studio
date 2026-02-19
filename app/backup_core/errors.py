class BackupError(Exception):
    """Base error for backup engine."""


class BackupConfigError(BackupError):
    """Raised when configuration is invalid or missing."""


class BackupIOError(BackupError):
    """Raised for unexpected I/O failures that should stop the backup."""


class BackupCancelled(BackupError):
    """Raised when a backup run is cancelled."""
