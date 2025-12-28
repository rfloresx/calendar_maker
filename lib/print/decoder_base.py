"""Shared decoder base with handler registration utilities.

Provides a minimal base class that manages handler registration used by
PrintDecoder and DrawDecoder variants to avoid duplicated boilerplate.
"""

from typing import Callable, Dict, Type


class DecoderBase:
    def __init__(self):
        self._handlers: Dict[Type, Callable] = {}

    def override(self, _type: Type):
        """Register a custom handler for a specific type and return a decorator."""
        def handler(func: Callable):
            self._handlers[_type] = func
            return func
        return handler

    def get_handler(self, _type: Type):
        return self._handlers.get(_type)
