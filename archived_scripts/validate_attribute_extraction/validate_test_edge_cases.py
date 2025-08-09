"""
Test file for edge cases in attribute extraction
"""
from dataclasses import dataclass
from typing import ClassVar, Union, Optional
import attr


class EmptyClass:
    """Class with no attributes"""
    pass


class OnlyMethods:
    """Class with only methods, no attributes"""
    
    def method_one(self):
        return "test"
    
    @property
    def prop_only(self):
        return "property"


@dataclass
class DataclassEdgeCases:
    """Edge cases for dataclass attribute extraction"""
    # Complex type annotations
    union_field: Union[str, int, None] = None
    nested_generic: Optional[list[dict[str, int]]] = None
    
    # ClassVar with complex types
    complex_class_var: ClassVar[dict[str, list[int]]] = {}
    
    # Field with metadata
    special_field: str = "default"


class PropertyOnlyClass:
    """Class with only properties"""
    
    @property
    def read_only(self) -> str:
        return "readonly"
    
    @property 
    def computed(self) -> int:
        return 42


class MultipleInheritance:
    """Base class for testing inheritance scenarios"""
    base_attr: str = "base"
    
    def __init__(self):
        self.base_instance = "base_instance"


@dataclass
class InheritedDataclass(MultipleInheritance):
    """Dataclass inheriting from regular class"""
    child_field: int = 0
    child_class_var: ClassVar[str] = "child"
    
    def __init__(self, child_field: int = 0):
        super().__init__()
        self.child_instance = "child_instance"
