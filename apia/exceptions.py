"""APIA exceptions."""


class ApiaError(Exception):
    """Base exception for all APIA errors."""


class RegistryError(ApiaError):
    """Raised when the registry cannot be loaded or is invalid."""


class ManifestNotFoundError(ApiaError):
    """Raised when a manifest cannot be found by the given id or criteria."""
