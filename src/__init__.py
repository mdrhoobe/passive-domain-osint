"""Passive Domain OSINT — ethical, single-domain public metadata research."""
from .collector import DomainCollector
from .validator import normalize_domain, validate_domain

__all__ = ["DomainCollector", "normalize_domain", "validate_domain"]
__version__ = "0.2.0"
