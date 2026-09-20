"""Public exceptions raised by contextual-curation."""


class CurationError(Exception):
    """Base exception for the package."""


class ConfigurationError(CurationError, ValueError):
    """Raised when a scoring configuration is invalid."""


class ConstraintError(CurationError, ValueError):
    """Raised when a constraint cannot be evaluated."""


class CompatibilityProviderError(CurationError):
    """Raised when pairwise compatibility evaluation cannot be completed."""

