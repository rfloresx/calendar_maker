from xml.etree import ElementTree as ET
from typing import Dict, Any


class HtmlTag(ET.Element):
    def __init__(self, tag: str, attrib={}, text: str = None, **extra):
        super().__init__(tag, attrib, **extra)
        if text:
            self.text = text

    def add(self, tag: str, attrib={}, text: str = None, **extra) -> 'HtmlTag':
        obj = HtmlTag(tag, attrib, text, **extra)
        self.append(obj)
        return obj


class HtmlEncoder:
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
        def handler(func):
            self._handles[_type] = func
            return func
        return handler

