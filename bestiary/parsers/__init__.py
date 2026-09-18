"""
Parsers package for Bestiary data.
"""
from .action_parser import (
    parse_action,
    parse_multiattack,
    parse_trait,
)

__all__ = [
    'parse_action',
    'parse_multiattack',
    'parse_trait',
]
