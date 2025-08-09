"""
Test file for dataclass attribute extraction validation
"""
from dataclasses import dataclass, field
from typing import ClassVar, List, Dict, Optional


@dataclass
class BasicDataclass:
    """Basic dataclass with instance and class variables"""
    # Instance variables (should be detected)
    name: str
    age: int = 25
    
    # ClassVar (should be detected as class attribute)
    instance_count: ClassVar[int] = 0
    
    def __init__(self):
        # Runtime attributes in __init__ (should be detected)
        self.runtime_attr = "dynamic"
        
    @property
    def computed_name(self) -> str:
        """Property (should be detected as property)"""
        return f"Name: {self.name}"


@dataclass
class ComplexDataclass:
    """Complex dataclass with various field types"""
    # Different types of fields
    items: List[str] = field(default_factory=list)
    metadata: Dict[str, int] = field(default_factory=dict)
    optional_field: Optional[str] = None
    
    # ClassVar in complex scenario
    schema_version: ClassVar[str] = "v1.0"
    total_instances: ClassVar[int] = 0
    
    # Private fields (should be excluded)
    _private_field: str = "hidden"
    
    # Properties
    @property 
    def item_count(self) -> int:
        return len(self.items)


class RegularClassWithClassVars:
    """Regular class with ClassVar annotations (not dataclass)"""
    # Should be detected as class attribute due to ClassVar
    counter: ClassVar[int] = 0
    config: ClassVar[Dict[str, str]] = {"setting": "value"}
    
    # Regular annotation without ClassVar - should be class attribute in regular class
    name: str
    
    def __init__(self, name: str):
        self.name = name
        self.instance_attr = "instance"
