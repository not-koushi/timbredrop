"""Application-specific exceptions used for friendly CLI errors."""


class TimbreDropError(Exception):
    """A user-facing error that does not require a traceback by default."""


class MissingDependencyError(TimbreDropError):
    """A required external executable is missing."""
