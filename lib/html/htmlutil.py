"""Helpers for building small HTML fragments using xml.etree.ElementTree.

HtmlTag is a thin Element subclass that makes creating nested tags easier.
HtmlEncoder is a small registry that maps Python types to functions that
produce HTML fragments (Element instances) for those types.
"""

from xml.etree import ElementTree as ET
from typing import Dict, Any


class HtmlTag(ET.Element):
    """Convenience Element subclass for creating HTML tags.

    HtmlTag(tag, attrib, text) builds an Element and provides an add()
    helper that appends and returns a new HtmlTag child.
    """
    def __init__(self, tag: str, attrib={}, text: str = None, **extra):
        super().__init__(tag, attrib, **extra)
        if text:
            self.text = text

    def add(self, tag: str, attrib={}, text: str = None, **extra) -> 'HtmlTag':
        """Append a child HtmlTag and return it for further construction."""
        obj = HtmlTag(tag, attrib, text, **extra)
        self.append(obj)
        return obj


class HtmlEncoder:
    """Registry that converts Python objects into ElementTree HTML fragments.

    Use override(type) as a decorator to register a function that accepts an
    instance of `type` and returns an ET.Element (or HtmlTag). The to_html()
    method dispatches using the registry or an object's __html__ method.
    """
    def __init__(self):
        self._handles = {}

    def to_html(self, obj):
        type_ = type(obj)
        ret = None
        if type_ in self._handles:
            ret = self._handles[type_](obj)
        elif hasattr(obj, '__html__'):
            ret = obj.__html__()
        else:
            raise ValueError(f"Unsuported Type {type_}")
        if ret is None:
            ret = HtmlTag(tag="div")
        return ret

    def override(self, _type: type):
        """Decorator to register a handler for `_type`.

        Example:
            @HtmlEncoder.override(MyType)
            def mytype_html(obj):
                return HtmlTag('div', text=str(obj))
        """
        def handler(func):
            self._handles[_type] = func
            return func
        return handler

