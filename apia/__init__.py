"""
APIA Python SDK
~~~~~~~~~~~~~~~
Python client for the APIA standard — AI-native API manifest discovery.

    >>> from apia import Registry
    >>> registry = Registry()
    >>> apis = registry.find("send telegram message")
    >>> print(apis[0].name)
    'Telegram Bot'
"""

from .registry import Registry
from .manifest import Manifest, Capability, Service, Auth
from .exceptions import ApiaError, ManifestNotFoundError, RegistryError

__version__ = "0.1.0"
__all__ = [
    "Registry",
    "Manifest",
    "Capability",
    "Service",
    "Auth",
    "ApiaError",
    "ManifestNotFoundError",
    "RegistryError",
]
