"""
Test file for attrs attribute extraction validation  
"""
import attr
import attrs
from typing import List, Dict


@attr.s
class AttrsClassDecorator:
    """Attrs class using @attr.s decorator"""
    name = attr.ib()
    age = attr.ib(default=30)
    items = attr.ib(factory=list)
    
    def __init__(self):
        # Runtime attributes (should be detected)
        self.runtime_value = "attrs_runtime"


@attrs.define
class AttrsDefineClass:
    """Modern attrs using @attrs.define"""
    title: str
    count: int = 0
    metadata: Dict[str, str] = attrs.field(factory=dict)
    
    @property
    def display_title(self) -> str:
        return f"Title: {self.title}"


@attrs.frozen
class AttrsFrozenClass:
    """Frozen attrs class"""
    id: str
    value: float = 1.0


class RegularClassWithSlots:
    """Regular class with __slots__"""
    __slots__ = ['name', 'value', 'items']
    
    # Class attribute
    default_name = "unknown"
    
    def __init__(self, name):
        self.name = name
        self.value = 42
        self.items = []
EOF < /dev/null
