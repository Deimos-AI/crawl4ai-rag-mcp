"""
Direct Neo4j GitHub Code Repository Extractor

Creates nodes and relationships directly in Neo4j without Graphiti:
- File nodes
- Class nodes  
- Method nodes
- Function nodes
- Import relationships

Bypasses all LLM processing for maximum speed.
"""

import asyncio
import logging
import os
import subprocess
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Dict, Any, Set
import sys
sys.path.append(str(Path(__file__).parent.parent / "src"))
try:
    from knowledge_graph.git_manager import GitRepositoryManager
except ImportError:
    # Fallback if running standalone
    GitRepositoryManager = None
import ast

from dotenv import load_dotenv
from neo4j import AsyncGraphDatabase

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger(__name__)


class Neo4jCodeAnalyzer:
    """Analyzes code for direct Neo4j insertion"""
    
    def __init__(self):
        # External modules to ignore
        self.external_modules = {
            # Python standard library
            'os', 'sys', 'json', 'logging', 'datetime', 'pathlib', 'typing', 'collections',
            'asyncio', 'subprocess', 'ast', 're', 'string', 'urllib', 'http', 'email',
            'time', 'uuid', 'hashlib', 'base64', 'itertools', 'functools', 'operator',
            'contextlib', 'copy', 'pickle', 'tempfile', 'shutil', 'glob', 'fnmatch',
            'io', 'codecs', 'locale', 'platform', 'socket', 'ssl', 'threading', 'queue',
            'multiprocessing', 'concurrent', 'warnings', 'traceback', 'inspect',
            'importlib', 'pkgutil', 'types', 'weakref', 'gc', 'dataclasses', 'enum',
            'abc', 'numbers', 'decimal', 'fractions', 'math', 'cmath', 'random', 'statistics',
            
            # Common third-party libraries
            'requests', 'urllib3', 'httpx', 'aiohttp', 'flask', 'django', 'fastapi',
            'pydantic', 'sqlalchemy', 'alembic', 'psycopg2', 'pymongo', 'redis',
            'celery', 'pytest', 'unittest', 'mock', 'faker', 'factory', 'hypothesis',
            'numpy', 'pandas', 'matplotlib', 'seaborn', 'scipy', 'sklearn', 'torch',
            'tensorflow', 'keras', 'opencv', 'pillow', 'boto3', 'botocore', 'azure',
            'google', 'openai', 'anthropic', 'langchain', 'transformers', 'huggingface_hub',
            'click', 'typer', 'rich', 'colorama', 'tqdm', 'python-dotenv', 'pyyaml',
            'toml', 'configargparse', 'marshmallow', 'attrs', 'dataclasses-json',
            'jsonschema', 'cerberus', 'voluptuous', 'schema', 'jinja2', 'mako',
            'cryptography', 'bcrypt', 'passlib', 'jwt', 'authlib', 'oauthlib'
        }
    
    def analyze_python_file(self, file_path: Path, repo_root: Path, project_modules: Set[str]) -> Dict[str, Any]:
        """Extract structure for direct Neo4j insertion"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content)
            relative_path = str(file_path.relative_to(repo_root))
            module_name = self._get_importable_module_name(file_path, repo_root, relative_path)
            
            # Extract structure
            classes = []
            functions = []
            imports = []
            
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    # Extract class with its methods and comprehensive attributes
                    methods = []
                    
                    for item in node.body:
                        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            if not item.name.startswith('_'):  # Public methods only
                                # Extract comprehensive parameter info
                                params = self._extract_function_parameters(item)
                                
                                # Get return type annotation
                                return_type = self._get_name(item.returns) if item.returns else 'Any'
                                
                                # Create detailed parameter list for Neo4j storage
                                params_detailed = []
                                for p in params:
                                    param_str = f"{p['name']}:{p['type']}"
                                    if p['optional'] and p['default'] is not None:
                                        param_str += f"={p['default']}"
                                    elif p['optional']:
                                        param_str += "=None"
                                    if p['kind'] != 'positional':
                                        param_str = f"[{p['kind']}] {param_str}"
                                    params_detailed.append(param_str)
                                
                                methods.append({
                                    'name': item.name,
                                    'params': params,  # Full parameter objects
                                    'params_detailed': params_detailed,  # Detailed string format
                                    'return_type': return_type,
                                    'args': [arg.arg for arg in item.args.args if arg.arg != 'self']  # Keep for backwards compatibility
                                })
                    
                    # Use comprehensive attribute extraction
                    attributes = self._extract_class_attributes(node)
                    
                    classes.append({
                        'name': node.name,
                        'full_name': f"{module_name}.{node.name}",
                        'methods': methods,
                        'attributes': attributes
                    })
                
                elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    # Only top-level functions
                    if not any(node in cls_node.body for cls_node in ast.walk(tree) if isinstance(cls_node, ast.ClassDef)):
                        if not node.name.startswith('_'):
                            # Extract comprehensive parameter info
                            params = self._extract_function_parameters(node)
                            
                            # Get return type annotation
                            return_type = self._get_name(node.returns) if node.returns else 'Any'
                            
                            # Create detailed parameter list for Neo4j storage
                            params_detailed = []
                            for p in params:
                                param_str = f"{p['name']}:{p['type']}"
                                if p['optional'] and p['default'] is not None:
                                    param_str += f"={p['default']}"
                                elif p['optional']:
                                    param_str += "=None"
                                if p['kind'] != 'positional':
                                    param_str = f"[{p['kind']}] {param_str}"
                                params_detailed.append(param_str)
                            
                            # Simple format for backwards compatibility
                            params_list = [f"{p['name']}:{p['type']}" for p in params]
                            
                            functions.append({
                                'name': node.name,
                                'full_name': f"{module_name}.{node.name}",
                                'params': params,  # Full parameter objects
                                'params_detailed': params_detailed,  # Detailed string format
                                'params_list': params_list,  # Simple string format for backwards compatibility
                                'return_type': return_type,
                                'args': [arg.arg for arg in node.args.args]  # Keep for backwards compatibility
                            })
                
                elif isinstance(node, (ast.Import, ast.ImportFrom)):
                    # Track internal imports only
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            if self._is_likely_internal(alias.name, project_modules):
                                imports.append(alias.name)
                    elif isinstance(node, ast.ImportFrom) and node.module:
                        if (node.module.startswith('.') or self._is_likely_internal(node.module, project_modules)):
                            imports.append(node.module)
            
            return {
                'module_name': module_name,
                'file_path': relative_path,
                'classes': classes,
                'functions': functions,
                'imports': list(set(imports)),  # Remove duplicates
                'line_count': len(content.splitlines())
            }
            
        except Exception as e:
            logger.warning(f"Could not analyze {file_path}: {e}")
            return None
    
    def _extract_class_attributes(self, class_node: ast.ClassDef) -> List[Dict[str, Any]]:
        """
        Comprehensively extract all class attributes including:
        - Instance attributes from __init__ methods (self.attr = value)
        - Type annotated attributes in __init__ (self.attr: Type = value)
        - Property decorators (@property def attr)
        - Class-level attributes (both annotated and non-annotated)
        - __slots__ definitions
        - Dataclass and attrs field definitions
        """
        attributes = []
        attribute_stats = {"total": 0, "dataclass": 0, "attrs": 0, "class_vars": 0, "properties": 0, "slots": 0}
        
        try:
            # Check if class has dataclass or attrs decorators
            is_dataclass = self._has_dataclass_decorator(class_node)
            is_attrs_class = self._has_attrs_decorator(class_node)
            
            # Extract class-level attributes
            for item in class_node.body:
                try:
                    # Type annotated class attributes
                    if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                        if not item.target.id.startswith('_'):
                            # FIXED: Check for ClassVar annotations before assuming dataclass/attrs semantics
                            is_class_var = self._is_class_var_annotation(item.annotation)
                            
                            # Determine attribute classification based on ClassVar and framework
                            if is_class_var:
                                # ClassVar attributes are always class attributes, regardless of framework
                                is_instance_attr = False
                                is_class_attr = True
                                attribute_stats["class_vars"] += 1
                            elif is_dataclass or is_attrs_class:
                                # In dataclass/attrs, non-ClassVar annotations are instance variables
                                is_instance_attr = True
                                is_class_attr = False
                                if is_dataclass:
                                    attribute_stats["dataclass"] += 1
                                if is_attrs_class:
                                    attribute_stats["attrs"] += 1
                            else:
                                # Regular classes: annotations without assignment are typically class-level type hints
                                is_instance_attr = False
                                is_class_attr = True
                            
                            attr_info = {
                                'name': item.target.id,
                                'type': self._get_name(item.annotation) if item.annotation else 'Any',
                                'is_instance': is_instance_attr,
                                'is_class': is_class_attr,
                                'is_property': False,
                                'has_type_hint': True,
                                'default_value': self._get_default_value(item.value) if item.value else None,
                                'line_number': item.lineno,
                                'from_dataclass': is_dataclass,
                                'from_attrs': is_attrs_class,
                                'is_class_var': is_class_var
                            }
                            attributes.append(attr_info)
                            attribute_stats["total"] += 1
                    
                    # Non-annotated class attributes
                    elif isinstance(item, ast.Assign):
                        # Check for __slots__
                        for target in item.targets:
                            if isinstance(target, ast.Name):
                                if target.id == '__slots__':
                                    slots = self._extract_slots(item.value)
                                    for slot_name in slots:
                                        if not slot_name.startswith('_'):
                                            attributes.append({
                                                'name': slot_name,
                                                'type': 'Any',
                                                'is_instance': True,  # slots are instance attributes
                                                'is_class': False,
                                                'is_property': False,
                                                'has_type_hint': False,
                                                'default_value': None,
                                                'line_number': item.lineno,
                                                'from_slots': True,
                                                'from_dataclass': False,
                                                'from_attrs': False,
                                                'is_class_var': False
                                            })
                                            attribute_stats["slots"] += 1
                                            attribute_stats["total"] += 1
                                elif not target.id.startswith('_'):
                                    # Regular class attribute
                                    attributes.append({
                                        'name': target.id,
                                        'type': self._infer_type_from_value(item.value) if item.value else 'Any',
                                        'is_instance': False,
                                        'is_class': True,
                                        'is_property': False,
                                        'has_type_hint': False,
                                        'default_value': self._get_default_value(item.value) if item.value else None,
                                        'line_number': item.lineno,
                                        'from_dataclass': False,
                                        'from_attrs': False,
                                        'is_class_var': False
                                    })
                                    attribute_stats["total"] += 1
                    
                    # Properties with @property decorator
                    elif isinstance(item, ast.FunctionDef) and not item.name.startswith('_'):
                        if any(isinstance(dec, ast.Name) and dec.id == 'property' 
                               for dec in item.decorator_list):
                            return_type = self._get_name(item.returns) if item.returns else 'Any'
                            attributes.append({
                                'name': item.name,
                                'type': return_type,
                                'is_instance': False,  # properties are accessed on instances but defined at class level
                                'is_class': False,
                                'is_property': True,
                                'has_type_hint': item.returns is not None,
                                'default_value': None,
                                'line_number': item.lineno,
                                'from_dataclass': False,
                                'from_attrs': False,
                                'is_class_var': False
                            })
                            attribute_stats["properties"] += 1
                            attribute_stats["total"] += 1
                
                except Exception as e:
                    logger.debug(f"Error extracting attribute from class body item: {e}")
                    continue
            
            # Extract attributes from __init__ method (unless it's a dataclass/attrs class with no __init__)
            init_attributes = self._extract_init_attributes(class_node)
            for init_attr in init_attributes:
                # Ensure init attributes have framework metadata
                init_attr.setdefault('from_dataclass', False)
                init_attr.setdefault('from_attrs', False)
                init_attr.setdefault('is_class_var', False)
            attributes.extend(init_attributes)
            attribute_stats["total"] += len(init_attributes)
            
            # IMPROVED: Enhanced deduplication logic that respects dataclass semantics
            unique_attributes = {}
            for attr in attributes:
                name = attr['name']
                if name not in unique_attributes:
                    unique_attributes[name] = attr
                else:
                    existing = unique_attributes[name]
                    should_replace = False
                    
                    # Priority 1: Dataclass/attrs fields take precedence over regular attributes
                    if (attr.get('from_dataclass') or attr.get('from_attrs')) and not (existing.get('from_dataclass') or existing.get('from_attrs')):
                        should_replace = True
                    # Priority 2: Type-hinted attributes over non-hinted (within same framework)
                    elif attr['has_type_hint'] and not existing['has_type_hint'] and not should_replace:
                        # Only if not already prioritizing dataclass/attrs
                        if not ((existing.get('from_dataclass') or existing.get('from_attrs')) and not (attr.get('from_dataclass') or attr.get('from_attrs'))):
                            should_replace = True
                    # Priority 3: Instance attributes over class attributes (within same framework and type hint status)
                    elif (attr['is_instance'] and not existing['is_instance'] and 
                          attr['has_type_hint'] == existing['has_type_hint'] and
                          not should_replace):
                        # Only if not already prioritizing by framework or type hints
                        existing_is_framework = existing.get('from_dataclass') or existing.get('from_attrs')
                        attr_is_framework = attr.get('from_dataclass') or attr.get('from_attrs')
                        if existing_is_framework == attr_is_framework:
                            should_replace = True
                    # Priority 4: Properties are always kept (they're unique)
                    elif attr.get('is_property') and not existing.get('is_property'):
                        should_replace = True
                    
                    if should_replace:
                        unique_attributes[name] = attr
            
            # Log attribute extraction statistics
            final_count = len(unique_attributes)
            if attribute_stats["total"] > 0:
                logger.debug(f"Extracted {final_count} unique attributes from {class_node.name}: "
                           f"dataclass={attribute_stats['dataclass']}, attrs={attribute_stats['attrs']}, "
                           f"class_vars={attribute_stats['class_vars']}, properties={attribute_stats['properties']}, "
                           f"slots={attribute_stats['slots']}, total_processed={attribute_stats['total']}")
            
            return list(unique_attributes.values())
            
        except Exception as e:
            logger.warning(f"Error extracting class attributes from {class_node.name}: {e}")
            return []

    def _has_dataclass_decorator(self, class_node: ast.ClassDef) -> bool:
        """Check if class has @dataclass decorator"""
        try:
            for decorator in class_node.decorator_list:
                if isinstance(decorator, ast.Name):
                    if decorator.id in ['dataclass', 'dataclasses']:
                        return True
                elif isinstance(decorator, ast.Attribute):
                    # Handle dataclasses.dataclass
                    attr_name = self._get_name(decorator)
                    if 'dataclass' in attr_name.lower():
                        return True
                elif isinstance(decorator, ast.Call):
                    # Handle @dataclass() with parameters
                    func_name = self._get_name(decorator.func)
                    if 'dataclass' in func_name.lower():
                        return True
        except Exception as e:
            logger.debug(f"Error checking dataclass decorator: {e}")
        return False
    
    def _has_attrs_decorator(self, class_node: ast.ClassDef) -> bool:
        """Check if class has @attrs decorator"""
        try:
            for decorator in class_node.decorator_list:
                if isinstance(decorator, ast.Name):
                    if decorator.id in ['attrs', 'attr']:
                        return True
                elif isinstance(decorator, ast.Attribute):
                    # Handle attr.s, attrs.define, etc.
                    attr_name = self._get_name(decorator)
                    if any(x in attr_name.lower() for x in ['attr.s', 'attr.define', 'attrs.define', 'attrs.frozen']):
                        return True
                elif isinstance(decorator, ast.Call):
                    # Handle @attr.s() with parameters
                    func_name = self._get_name(decorator.func)
                    if any(x in func_name.lower() for x in ['attr.s', 'attr.define', 'attrs.define', 'attrs.frozen']):
                        return True
        except Exception as e:
            logger.debug(f"Error checking attrs decorator: {e}")
        return False

    def _is_class_var_annotation(self, annotation_node) -> bool:
        """
        Check if an annotation is a ClassVar type.
        Handles patterns like ClassVar[int], typing.ClassVar[str], etc.
        """
        if annotation_node is None:
            return False
        
        try:
            annotation_str = self._get_name(annotation_node)
            return 'ClassVar' in annotation_str
        except Exception as e:
            logger.debug(f"Error checking ClassVar annotation: {e}")
            return False
    def _extract_init_attributes(self, class_node: ast.ClassDef) -> List[Dict[str, Any]]:
        """Extract attributes from __init__ method"""
        attributes = []
        
        # Find __init__ method
        init_method = None
        for item in class_node.body:
            if isinstance(item, ast.FunctionDef) and item.name == '__init__':
                init_method = item
                break
        
        if not init_method:
            return attributes
        
        try:
            for node in ast.walk(init_method):
                try:
                    # Handle annotated assignments: self.attr: Type = value
                    if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Attribute):
                        if (isinstance(node.target.value, ast.Name) and 
                            node.target.value.id == 'self' and 
                            not node.target.attr.startswith('_')):
                            
                            attributes.append({
                                'name': node.target.attr,
                                'type': self._get_name(node.annotation) if node.annotation else 'Any',
                                'is_instance': True,
                                'is_class': False,
                                'is_property': False,
                                'has_type_hint': True,
                                'default_value': self._get_default_value(node.value) if node.value else None,
                                'line_number': node.lineno
                            })
                    
                    # Handle regular assignments: self.attr = value
                    elif isinstance(node, ast.Assign):
                        for target in node.targets:
                            if isinstance(target, ast.Attribute):
                                if (isinstance(target.value, ast.Name) and 
                                    target.value.id == 'self' and 
                                    not target.attr.startswith('_')):
                                    
                                    # Try to infer type from assignment value
                                    inferred_type = self._infer_type_from_value(node.value)
                                    
                                    attributes.append({
                                        'name': target.attr,
                                        'type': inferred_type,
                                        'is_instance': True,
                                        'is_class': False,
                                        'is_property': False,
                                        'has_type_hint': False,
                                        'default_value': self._get_default_value(node.value),
                                        'line_number': node.lineno
                                    })
                            
                            # Handle multiple assignments: self.x = self.y = value
                            elif isinstance(target, ast.Tuple):
                                for elt in target.elts:
                                    if (isinstance(elt, ast.Attribute) and 
                                        isinstance(elt.value, ast.Name) and 
                                        elt.value.id == 'self' and 
                                        not elt.attr.startswith('_')):
                                        
                                        inferred_type = self._infer_type_from_value(node.value)
                                        attributes.append({
                                            'name': elt.attr,
                                            'type': inferred_type,
                                            'is_instance': True,
                                            'is_class': False,
                                            'is_property': False,
                                            'has_type_hint': False,
                                            'default_value': self._get_default_value(node.value),
                                            'line_number': node.lineno
                                        })
                
                except Exception as e:
                    logger.debug(f"Error extracting __init__ attribute: {e}")
                    continue
        
        except Exception as e:
            logger.debug(f"Error walking __init__ method: {e}")
        
        return attributes

    def _extract_slots(self, slots_node) -> List[str]:
        """Extract slot names from __slots__ definition"""
        slots = []
        
        try:
            if isinstance(slots_node, (ast.List, ast.Tuple)):
                for elt in slots_node.elts:
                    if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                        slots.append(elt.value)
                    elif isinstance(elt, ast.Str):  # Python < 3.8 compatibility
                        slots.append(elt.s)
            elif isinstance(slots_node, ast.Constant) and isinstance(slots_node.value, str):
                slots.append(slots_node.value)
            elif isinstance(slots_node, ast.Str):  # Python < 3.8 compatibility
                slots.append(slots_node.s)
        
        except Exception as e:
            logger.debug(f"Error extracting slots: {e}")
        
        return slots

    def _infer_type_from_value(self, value_node) -> str:
        """Attempt to infer type from assignment value with enhanced patterns"""
        try:
            if isinstance(value_node, ast.Constant):
                if isinstance(value_node.value, bool):
                    return 'bool'
                elif isinstance(value_node.value, int):
                    return 'int'
                elif isinstance(value_node.value, float):
                    return 'float'
                elif isinstance(value_node.value, str):
                    return 'str'
                elif isinstance(value_node.value, bytes):
                    return 'bytes'
                elif value_node.value is None:
                    return 'Optional[Any]'
            elif isinstance(value_node, (ast.List, ast.ListComp)):
                return 'List[Any]'
            elif isinstance(value_node, (ast.Dict, ast.DictComp)):
                return 'Dict[Any, Any]'
            elif isinstance(value_node, (ast.Set, ast.SetComp)):
                return 'Set[Any]'
            elif isinstance(value_node, ast.Tuple):
                return 'Tuple[Any, ...]'
            elif isinstance(value_node, ast.Call):
                # Try to get type from function call
                func_name = self._get_name(value_node.func)
                if func_name in ['list', 'dict', 'set', 'tuple', 'str', 'int', 'float', 'bool']:
                    return func_name
                elif func_name in ['defaultdict', 'Counter', 'OrderedDict']:
                    return f'collections.{func_name}'
                elif func_name in ['deque']:
                    return 'collections.deque'
                elif func_name in ['Path']:
                    return 'pathlib.Path'
                elif func_name in ['datetime', 'date', 'time']:
                    return f'datetime.{func_name}'
                elif func_name in ['UUID']:
                    return 'uuid.UUID'
                elif func_name in ['re.compile', 'compile']:
                    return 're.Pattern'
                # Handle dataclass/attrs field calls
                elif 'field' in func_name.lower():
                    return 'Any'  # Field type should be inferred from annotation
                return 'Any'  # Unknown function call
            elif isinstance(value_node, ast.Attribute):
                # Handle attribute access like self.other_attr, module.CONSTANT
                attr_name = self._get_name(value_node)
                if 'CONSTANT' in attr_name.upper() or attr_name.isupper():
                    return 'Any'  # Constants could be anything
                return 'Any'
            elif isinstance(value_node, ast.Name):
                # Handle variable references
                if value_node.id in ['True', 'False']:
                    return 'bool'
                elif value_node.id in ['None']:
                    return 'Optional[Any]'
                else:
                    return 'Any'  # Could be any variable
            elif isinstance(value_node, ast.BinOp):
                # Handle binary operations - try to infer from operands
                return 'Any'  # Could be various types depending on operation
        except Exception as e:
            logger.debug(f"Error in type inference: {e}")
        
        return 'Any'
    def _is_likely_internal(self, import_name: str, project_modules: Set[str]) -> bool:
        """Check if an import is likely internal to the project"""
        if not import_name:
            return False
        
        # Relative imports are definitely internal
        if import_name.startswith('.'):
            return True
        
        # Check if it's a known external module
        base_module = import_name.split('.')[0]
        if base_module in self.external_modules:
            return False
        
        # Check if it matches any project module
        for project_module in project_modules:
            if import_name.startswith(project_module):
                return True
        
        # If it's not obviously external, consider it internal
        if (not any(ext in base_module.lower() for ext in ['test', 'mock', 'fake']) and
            not base_module.startswith('_') and
            len(base_module) > 2):
            return True
        
        return False
    
    def _get_importable_module_name(self, file_path: Path, repo_root: Path, relative_path: str) -> str:
        """Determine the actual importable module name for a Python file"""
        # Start with the default: convert file path to module path
        default_module = relative_path.replace('/', '.').replace('\\', '.').replace('.py', '')
        
        # Common patterns to detect the actual package root
        path_parts = Path(relative_path).parts
        
        # Look for common package indicators
        package_roots = []
        
        # Check each directory level for __init__.py to find package boundaries
        current_path = repo_root
        for i, part in enumerate(path_parts[:-1]):  # Exclude the .py file itself
            current_path = current_path / part
            if (current_path / '__init__.py').exists():
                # This is a package directory, mark it as a potential root
                package_roots.append(i)
        
        if package_roots:
            # Use the first (outermost) package as the root
            package_start = package_roots[0]
            module_parts = path_parts[package_start:]
            module_name = '.'.join(module_parts).replace('.py', '')
            return module_name
        
        # Fallback: look for common Python project structures
        # Skip common non-package directories
        skip_dirs = {'src', 'lib', 'source', 'python', 'pkg', 'packages'}
        
        # Find the first directory that's not in skip_dirs
        filtered_parts = []
        for part in path_parts:
            if part.lower() not in skip_dirs or filtered_parts:  # Once we start including, include everything
                filtered_parts.append(part)
        
        if filtered_parts:
            module_name = '.'.join(filtered_parts).replace('.py', '')
            return module_name
        
        # Final fallback: use the default
        return default_module
    
    def _extract_function_parameters(self, func_node):
        """Comprehensive parameter extraction from function definition"""
        params = []
        
        # Regular positional arguments
        for i, arg in enumerate(func_node.args.args):
            if arg.arg == 'self':
                continue
                
            param_info = {
                'name': arg.arg,
                'type': self._get_name(arg.annotation) if arg.annotation else 'Any',
                'kind': 'positional',
                'optional': False,
                'default': None
            }
            
            # Check if this argument has a default value
            defaults_start = len(func_node.args.args) - len(func_node.args.defaults)
            if i >= defaults_start:
                default_idx = i - defaults_start
                if default_idx < len(func_node.args.defaults):
                    param_info['optional'] = True
                    param_info['default'] = self._get_default_value(func_node.args.defaults[default_idx])
            
            params.append(param_info)
        
        # *args parameter
        if func_node.args.vararg:
            params.append({
                'name': f"*{func_node.args.vararg.arg}",
                'type': self._get_name(func_node.args.vararg.annotation) if func_node.args.vararg.annotation else 'Any',
                'kind': 'var_positional',
                'optional': True,
                'default': None
            })
        
        # Keyword-only arguments (after *)
        for i, arg in enumerate(func_node.args.kwonlyargs):
            param_info = {
                'name': arg.arg,
                'type': self._get_name(arg.annotation) if arg.annotation else 'Any',
                'kind': 'keyword_only',
                'optional': True,  # All kwonly args are optional unless explicitly required
                'default': None
            }
            
            # Check for default value
            if i < len(func_node.args.kw_defaults) and func_node.args.kw_defaults[i] is not None:
                param_info['default'] = self._get_default_value(func_node.args.kw_defaults[i])
            else:
                param_info['optional'] = False  # No default = required kwonly arg
            
            params.append(param_info)
        
        # **kwargs parameter
        if func_node.args.kwarg:
            params.append({
                'name': f"**{func_node.args.kwarg.arg}",
                'type': self._get_name(func_node.args.kwarg.annotation) if func_node.args.kwarg.annotation else 'Dict[str, Any]',
                'kind': 'var_keyword',
                'optional': True,
                'default': None
            })
        
        return params
    
    def _get_default_value(self, default_node):
        """Extract default value from AST node"""
        try:
            if isinstance(default_node, ast.Constant):
                return repr(default_node.value)
            elif isinstance(default_node, ast.Name):
                return default_node.id
            elif isinstance(default_node, ast.Attribute):
                return self._get_name(default_node)
            elif isinstance(default_node, ast.List):
                return "[]"
            elif isinstance(default_node, ast.Dict):
                return "{}"
            else:
                return "..."
        except Exception:
            return "..."
    
    def _get_name(self, node):
        """Extract name from AST node, handling complex types safely"""
        if node is None:
            return "Any"
        
        try:
            if isinstance(node, ast.Name):
                return node.id
            elif isinstance(node, ast.Attribute):
                if hasattr(node, 'value'):
                    return f"{self._get_name(node.value)}.{node.attr}"
                else:
                    return node.attr
            elif isinstance(node, ast.Subscript):
                # Handle List[Type], Dict[K,V], etc.
                base = self._get_name(node.value)
                if hasattr(node, 'slice'):
                    if isinstance(node.slice, ast.Name):
                        return f"{base}[{node.slice.id}]"
                    elif isinstance(node.slice, ast.Tuple):
                        elts = [self._get_name(elt) for elt in node.slice.elts]
                        return f"{base}[{', '.join(elts)}]"
                    elif isinstance(node.slice, ast.Constant):
                        return f"{base}[{repr(node.slice.value)}]"
                    elif isinstance(node.slice, ast.Attribute):
                        return f"{base}[{self._get_name(node.slice)}]"
                    elif isinstance(node.slice, ast.Subscript):
                        return f"{base}[{self._get_name(node.slice)}]"
                    else:
                        # Try to get the name of the slice, fallback to Any if it fails
                        try:
                            slice_name = self._get_name(node.slice)
                            return f"{base}[{slice_name}]"
                        except:
                            return f"{base}[Any]"
                return base
            elif isinstance(node, ast.Constant):
                return str(node.value)
            elif isinstance(node, ast.Str):  # Python < 3.8
                return f'"{node.s}"'
            elif isinstance(node, ast.Tuple):
                elts = [self._get_name(elt) for elt in node.elts]
                return f"({', '.join(elts)})"
            elif isinstance(node, ast.List):
                elts = [self._get_name(elt) for elt in node.elts]
                return f"[{', '.join(elts)}]"
            else:
                # Fallback for complex types - return a simple string representation
                return "Any"
        except Exception:
            # If anything goes wrong, return a safe default
            return "Any"


class DirectNeo4jExtractor:
    """Creates nodes and relationships directly in Neo4j"""
    
    def __init__(self, neo4j_uri: str, neo4j_user: str, neo4j_password: str):
        self.neo4j_uri = neo4j_uri
        self.neo4j_user = neo4j_user
        self.neo4j_password = neo4j_password
        self.driver = None
        self.analyzer = Neo4jCodeAnalyzer()
        self.git_manager = GitRepositoryManager() if GitRepositoryManager else None
    
    async def initialize(self):
        """Initialize Neo4j connection"""
        logger.info("Initializing Neo4j connection...")
        
        # Import notification suppression (available in neo4j>=5.21.0)
        try:
            from neo4j import NotificationMinimumSeverity
            # Create Neo4j driver with notification suppression
            self.driver = AsyncGraphDatabase.driver(
                self.neo4j_uri, 
                auth=(self.neo4j_user, self.neo4j_password),
                warn_notification_severity=NotificationMinimumSeverity.OFF
            )
        except (ImportError, AttributeError):
            # Fallback for older versions - use logging suppression
            import logging
            logging.getLogger('neo4j.notifications').setLevel(logging.ERROR)
            self.driver = AsyncGraphDatabase.driver(
                self.neo4j_uri, 
                auth=(self.neo4j_user, self.neo4j_password)
            )
        
        # Clear existing data
        # logger.info("Clearing existing data...")
        # async with self.driver.session() as session:
        #     await session.run("MATCH (n) DETACH DELETE n")
        logger.info("Neo4j connection initialized successfully")
    
    async def clear_repository_data(self, repo_name: str):
        """Clear all data for a specific repository with production-ready error handling and transaction management.
        
        This method uses a single Neo4j transaction to ensure atomicity - either all cleanup operations 
        succeed or none are applied. The deletion order follows dependency hierarchy to prevent constraint violations:
        1. Methods and Attributes (depend on Classes)
        2. Functions (depend on Files) 
        3. Classes (depend on Files)
        4. Files (depend on Repository)
        5. Branches and Commits (depend on Repository)
        6. Repository (root node)
        
        Args:
            repo_name: Name of the repository to clear
            
        Raises:
            Exception: If repository validation fails or Neo4j operations encounter errors
        """
        logger.info(f"Starting cleanup for repository: {repo_name}")
        
        # Validate that repository exists before attempting cleanup
        async with self.driver.session() as session:
            try:
                result = await session.run(
                    "MATCH (r:Repository {name: $repo_name}) RETURN count(r) as repo_count",
                    repo_name=repo_name
                )
                record = await result.single()
                if not record or record["repo_count"] == 0:
                    logger.warning(f"Repository '{repo_name}' not found in database - nothing to clean")
                    return
                    
                logger.info(f"Confirmed repository '{repo_name}' exists, proceeding with cleanup")
            except Exception as e:
                logger.error(f"Failed to validate repository '{repo_name}': {e}")
                raise Exception(f"Repository validation failed: {e}")
        
        # Track cleanup statistics for logging
        cleanup_stats = {
            "methods": 0,
            "attributes": 0, 
            "functions": 0,
            "classes": 0,
            "files": 0,
            "branches": 0,
            "commits": 0,
            "repository": 0
        }
        
        # Execute all cleanup operations within a single transaction
        async with self.driver.session() as session:
            tx = await session.begin_transaction()
            try:
                logger.info("Starting transactional cleanup operations...")
                
                # Step 1: Delete methods and attributes (they depend on classes)
                logger.debug("Deleting methods...")
                result = await tx.run("""
                    MATCH (r:Repository {name: $repo_name})-[:CONTAINS]->(f:File)-[:DEFINES]->(c:Class)
                    OPTIONAL MATCH (c)-[:HAS_METHOD]->(m:Method)
                    DETACH DELETE m
                    RETURN count(m) as deleted_count
                """, repo_name=repo_name)
                record = await result.single()
                cleanup_stats["methods"] = record["deleted_count"] if record else 0
                
                logger.debug("Deleting attributes...")
                result = await tx.run("""
                    MATCH (r:Repository {name: $repo_name})-[:CONTAINS]->(f:File)-[:DEFINES]->(c:Class)
                    OPTIONAL MATCH (c)-[:HAS_ATTRIBUTE]->(a:Attribute)
                    DETACH DELETE a
                    RETURN count(a) as deleted_count
                """, repo_name=repo_name)
                record = await result.single()
                cleanup_stats["attributes"] = record["deleted_count"] if record else 0
                
                # Step 2: Delete functions (they depend on files)
                logger.debug("Deleting functions...")
                result = await tx.run("""
                    MATCH (r:Repository {name: $repo_name})-[:CONTAINS]->(f:File)
                    OPTIONAL MATCH (f)-[:DEFINES]->(func:Function)
                    DETACH DELETE func
                    RETURN count(func) as deleted_count
                """, repo_name=repo_name)
                record = await result.single()
                cleanup_stats["functions"] = record["deleted_count"] if record else 0
                
                # Step 3: Delete classes (they depend on files)
                logger.debug("Deleting classes...")
                result = await tx.run("""
                    MATCH (r:Repository {name: $repo_name})-[:CONTAINS]->(f:File)
                    OPTIONAL MATCH (f)-[:DEFINES]->(c:Class)
                    DETACH DELETE c
                    RETURN count(c) as deleted_count
                """, repo_name=repo_name)
                record = await result.single()
                cleanup_stats["classes"] = record["deleted_count"] if record else 0
                
                # Step 4: Delete files (they depend on repository)
                logger.debug("Deleting files...")
                result = await tx.run("""
                    MATCH (r:Repository {name: $repo_name})
                    OPTIONAL MATCH (r)-[:CONTAINS]->(f:File)
                    DETACH DELETE f
                    RETURN count(f) as deleted_count
                """, repo_name=repo_name)
                record = await result.single()
                cleanup_stats["files"] = record["deleted_count"] if record else 0
                
                # Step 5: Delete branches and commits (they depend on repository)
                # This is the key fix for HAS_COMMIT relationship warnings
                logger.debug("Deleting branches...")
                result = await tx.run("""
                    MATCH (r:Repository {name: $repo_name})
                    OPTIONAL MATCH (r)-[:HAS_BRANCH]->(b:Branch)
                    DETACH DELETE b
                    RETURN count(b) as deleted_count
                """, repo_name=repo_name)
                record = await result.single()
                cleanup_stats["branches"] = record["deleted_count"] if record else 0
                
                logger.debug("Deleting commits...")
                result = await tx.run("""
                    MATCH (r:Repository {name: $repo_name})
                    OPTIONAL MATCH (r)-[:HAS_COMMIT]->(c:Commit)
                    DETACH DELETE c
                    RETURN count(c) as deleted_count
                """, repo_name=repo_name)
                record = await result.single()
                cleanup_stats["commits"] = record["deleted_count"] if record else 0
                
                # Step 6: Finally delete the repository
                logger.debug("Deleting repository...")
                result = await tx.run("""
                    MATCH (r:Repository {name: $repo_name})
                    DETACH DELETE r
                    RETURN count(r) as deleted_count
                """, repo_name=repo_name)
                record = await result.single()
                cleanup_stats["repository"] = record["deleted_count"] if record else 0
                
                # Commit the transaction
                await tx.commit()
                logger.info("Transaction committed successfully")
                
            except Exception as e:
                # Rollback the transaction on any error
                logger.error(f"Error during cleanup transaction, rolling back: {e}")
                await tx.rollback()
                raise Exception(f"Repository cleanup failed and was rolled back: {e}")
        
        # Log cleanup statistics
        total_deleted = sum(cleanup_stats.values())
        logger.info(f"Successfully cleared repository '{repo_name}' - {total_deleted} total nodes deleted:")
        for entity_type, count in cleanup_stats.items():
            if count > 0:
                logger.info(f"  - {entity_type}: {count}")
        
        if total_deleted == 0:
            logger.info("Repository was already empty or contained no data to clean")
    
    async def close(self):
        """Close Neo4j connection"""
        if self.driver:
            await self.driver.close()
    
    async def clone_repo(self, repo_url: str, target_dir: str, branch: Optional[str] = None) -> str:
        """Clone repository with enhanced Git support"""
        logger.info(f"Cloning repository to: {target_dir}")
        
        # Use GitRepositoryManager if available for enhanced features
        if self.git_manager:
            try:
                import asyncio
                # GitRepositoryManager provides branch support and better error handling
                result = await self.git_manager.clone_repository(
                    url=repo_url, 
                    target_dir=target_dir,
                    branch=branch,
                    depth=1,  # Keep shallow clone for performance
                    single_branch=True if branch else False
                )
                return result
            except Exception as e:
                logger.warning(f"GitRepositoryManager failed, falling back to subprocess: {e}")
        
        # Fallback to original implementation
        if os.path.exists(target_dir):
            logger.info(f"Removing existing directory: {target_dir}")
            try:
                def handle_remove_readonly(func, path, exc):
                    try:
                        if os.path.exists(path):
                            os.chmod(path, 0o777)
                            func(path)
                    except PermissionError:
                        logger.warning(f"Could not remove {path} - file in use, skipping")
                        pass
                shutil.rmtree(target_dir, onerror=handle_remove_readonly)
            except Exception as e:
                logger.warning(f"Could not fully remove {target_dir}: {e}. Proceeding anyway...")
        
        logger.info(f"Running git clone from {repo_url}")
        cmd = ['git', 'clone', '--depth', '1']
        if branch:
            cmd.extend(['--branch', branch])
        cmd.extend([repo_url, target_dir])
        
        subprocess.run(cmd, check=True)
        logger.info("Repository cloned successfully")
        return target_dir

    async def get_repository_metadata(self, repo_dir: str) -> Dict:
        """Extract Git repository metadata using GitRepositoryManager"""
        metadata = {
            "branches": [],
            "tags": [],
            "recent_commits": [],
            "info": {}
        }
        
        if self.git_manager:
            try:
                # Get repository info
                metadata["info"] = await self.git_manager.get_repository_info(repo_dir)
                
                # Get branches
                metadata["branches"] = await self.git_manager.get_branches(repo_dir)
                
                # Get tags
                metadata["tags"] = await self.git_manager.get_tags(repo_dir)
                
                # Get recent commits (last 10)
                metadata["recent_commits"] = await self.git_manager.get_commits(repo_dir, limit=10)
                
                logger.info(f"Extracted Git metadata: {len(metadata['branches'])} branches, "
                          f"{len(metadata['tags'])} tags, {len(metadata['recent_commits'])} commits")
            except Exception as e:
                logger.warning(f"Could not extract Git metadata: {e}")
        
        return metadata
    
    def get_python_files(self, repo_path: str) -> List[Path]:
        """Get Python files, focusing on main source directories"""
        python_files = []
        exclude_dirs = {
            'tests', 'test', '__pycache__', '.git', 'venv', 'env',
            'node_modules', 'build', 'dist', '.pytest_cache', 'docs',
            'examples', 'example', 'demo', 'benchmark'
        }
        
        for root, dirs, files in os.walk(repo_path):
            dirs[:] = [d for d in dirs if d not in exclude_dirs and not d.startswith('.')]
            
            for file in files:
                if file.endswith('.py') and not file.startswith('test_'):
                    file_path = Path(root) / file
                    if (file_path.stat().st_size < 500_000 and 
                        file not in ['setup.py', 'conftest.py']):
                        python_files.append(file_path)
        
        return python_files
    
    async def analyze_repository(self, repo_url: str, temp_dir: str = None, branch: str = None):
        """Analyze repository and create nodes/relationships in Neo4j"""
        repo_name = repo_url.split('/')[-1].replace('.git', '')
        logger.info(f"Analyzing repository: {repo_name}")
        
        # Clear existing data for this repository before re-processing
        await self.clear_repository_data(repo_name)
        
        # Set default temp_dir to repos folder at script level
        if temp_dir is None:
            script_dir = Path(__file__).parent
            temp_dir = str(script_dir / "repos" / repo_name)
        
        # Clone and analyze
        repo_path = Path(await self.clone_repo(repo_url, temp_dir, branch))
        
        try:
            logger.info("Getting Python files...")
            python_files = self.get_python_files(str(repo_path))
            logger.info(f"Found {len(python_files)} Python files to analyze")
            
            # First pass: identify project modules
            logger.info("Identifying project modules...")
            project_modules = set()
            for file_path in python_files:
                relative_path = str(file_path.relative_to(repo_path))
                module_parts = relative_path.replace('/', '.').replace('.py', '').split('.')
                if len(module_parts) > 0 and not module_parts[0].startswith('.'):
                    project_modules.add(module_parts[0])
            
            logger.info(f"Identified project modules: {sorted(project_modules)}")
            
            # Second pass: analyze files and collect data
            logger.info("Analyzing Python files...")
            modules_data = []
            for i, file_path in enumerate(python_files):
                if i % 20 == 0:
                    logger.info(f"Analyzing file {i+1}/{len(python_files)}: {file_path.name}")
                
                analysis = self.analyzer.analyze_python_file(file_path, repo_path, project_modules)
                if analysis:
                    modules_data.append(analysis)
            
            logger.info(f"Found {len(modules_data)} files with content")
            
            # Get Git metadata if available
            git_metadata = await self.get_repository_metadata(str(repo_path))
            
            # Create nodes and relationships in Neo4j
            logger.info("Creating nodes and relationships in Neo4j...")
            await self._create_graph(repo_name, modules_data, git_metadata)
            
            # Print summary
            total_classes = sum(len(mod['classes']) for mod in modules_data)
            total_methods = sum(len(cls['methods']) for mod in modules_data for cls in mod['classes'])
            total_functions = sum(len(mod['functions']) for mod in modules_data)
            total_imports = sum(len(mod['imports']) for mod in modules_data)
            
            logger.info(f"\n=== Direct Neo4j Repository Analysis for {repo_name} ===")
            logger.info(f"Files processed: {len(modules_data)}")
            logger.info(f"Classes created: {total_classes}")
            logger.info(f"Methods created: {total_methods}")
            logger.info(f"Functions created: {total_functions}")
            logger.info(f"Import relationships: {total_imports}")
            
            logger.info(f"Successfully created Neo4j graph for {repo_name}")
            
        finally:
            if os.path.exists(temp_dir):
                logger.info(f"Cleaning up temporary directory: {temp_dir}")
                try:
                    def handle_remove_readonly(func, path, exc):
                        try:
                            if os.path.exists(path):
                                os.chmod(path, 0o777)
                                func(path)
                        except PermissionError:
                            logger.warning(f"Could not remove {path} - file in use, skipping")
                            pass
                    
                    shutil.rmtree(temp_dir, onerror=handle_remove_readonly)
                    logger.info("Cleanup completed")
                except Exception as e:
                    logger.warning(f"Cleanup failed: {e}. Directory may remain at {temp_dir}")
                    # Don't fail the whole process due to cleanup issues
    
    async def _create_graph(self, repo_name: str, modules_data: List[Dict], git_metadata: Dict = None):
        """Create all nodes and relationships in Neo4j"""
        
        async with self.driver.session() as session:
            # Create Repository node with enhanced metadata
            repo_properties = {
                "name": repo_name,
                "created_at": "datetime()"
            }
            
            # Add Git metadata if available
            if git_metadata and git_metadata.get("info"):
                info = git_metadata["info"]
                repo_properties.update({
                    "remote_url": info.get("remote_url", ""),
                    "current_branch": info.get("current_branch", "main"),
                    "file_count": info.get("file_count", 0),
                    "contributor_count": info.get("contributor_count", 0),
                    "size": info.get("size", "unknown")
                })
            
            # Create repository with all properties
            await session.run(
                """CREATE (r:Repository {
                    name: $name,
                    remote_url: $remote_url,
                    current_branch: $current_branch,
                    file_count: $file_count,
                    contributor_count: $contributor_count,
                    size: $size,
                    created_at: datetime()
                })""",
                name=repo_name,
                remote_url=repo_properties.get("remote_url", ""),
                current_branch=repo_properties.get("current_branch", "main"),
                file_count=repo_properties.get("file_count", 0),
                contributor_count=repo_properties.get("contributor_count", 0),
                size=repo_properties.get("size", "unknown")
            )
            
            nodes_created = 0
            relationships_created = 0
            
            for i, mod in enumerate(modules_data):
                # 1. Create File node
                await session.run("""
                    CREATE (f:File {
                        name: $name,
                        path: $path,
                        module_name: $module_name,
                        line_count: $line_count,
                        created_at: datetime()
                    })
                """, 
                    name=mod['file_path'].split('/')[-1],
                    path=mod['file_path'],
                    module_name=mod['module_name'],
                    line_count=mod['line_count']
                )
                nodes_created += 1
                
                # 2. Connect File to Repository
                await session.run("""
                    MATCH (r:Repository {name: $repo_name})
                    MATCH (f:File {path: $file_path})
                    CREATE (r)-[:CONTAINS]->(f)
                """, repo_name=repo_name, file_path=mod['file_path'])
                relationships_created += 1
                
                # 3. Create Class nodes and relationships
                for cls in mod['classes']:
                    # Create Class node using MERGE to avoid duplicates
                    await session.run("""
                        MERGE (c:Class {full_name: $full_name})
                        ON CREATE SET c.name = $name, c.created_at = datetime()
                    """, name=cls['name'], full_name=cls['full_name'])
                    nodes_created += 1
                    
                    # Connect File to Class
                    await session.run("""
                        MATCH (f:File {path: $file_path})
                        MATCH (c:Class {full_name: $class_full_name})
                        MERGE (f)-[:DEFINES]->(c)
                    """, file_path=mod['file_path'], class_full_name=cls['full_name'])
                    relationships_created += 1
                    
                    # 4. Create Method nodes - use MERGE to avoid duplicates
                    for method in cls['methods']:
                        method_full_name = f"{cls['full_name']}.{method['name']}"
                        # Create method with unique ID to avoid conflicts
                        method_id = f"{cls['full_name']}::{method['name']}"
                        
                        await session.run("""
                            MERGE (m:Method {method_id: $method_id})
                            ON CREATE SET m.name = $name, 
                                         m.full_name = $full_name,
                                         m.args = $args,
                                         m.params_list = $params_list,
                                         m.params_detailed = $params_detailed,
                                         m.return_type = $return_type,
                                         m.created_at = datetime()
                        """, 
                            name=method['name'], 
                            full_name=method_full_name,
                            method_id=method_id,
                            args=method['args'],
                            params_list=[f"{p['name']}:{p['type']}" for p in method['params']],  # Simple format
                            params_detailed=method.get('params_detailed', []),  # Detailed format
                            return_type=method['return_type']
                        )
                        nodes_created += 1
                        
                        # Connect Class to Method
                        await session.run("""
                            MATCH (c:Class {full_name: $class_full_name})
                            MATCH (m:Method {method_id: $method_id})
                            MERGE (c)-[:HAS_METHOD]->(m)
                        """, 
                            class_full_name=cls['full_name'], 
                            method_id=method_id
                        )
                        relationships_created += 1
                    
                    # 5. Create Enhanced Attribute nodes - FIXED: Now storing all extracted metadata
                    for attr in cls['attributes']:
                        attr_full_name = f"{cls['full_name']}.{attr['name']}"
                        # Create attribute with unique ID to avoid conflicts
                        attr_id = f"{cls['full_name']}::{attr['name']}"
                        
                        # FIXED: Extract all available attribute metadata including framework metadata
                        attr_data = {
                            'name': attr['name'],
                            'full_name': attr_full_name,
                            'attr_id': attr_id,
                            'type': attr.get('type', 'Any'),
                            'default_value': attr.get('default_value'),
                            'is_instance': attr.get('is_instance', False),
                            'is_class': attr.get('is_class', False),
                            'is_property': attr.get('is_property', False),
                            'has_type_hint': attr.get('has_type_hint', False),
                            'line_number': attr.get('line_number', 0),
                            'from_slots': attr.get('from_slots', False),
                            'from_dataclass': attr.get('from_dataclass', False),
                            'from_attrs': attr.get('from_attrs', False),
                            'is_class_var': attr.get('is_class_var', False)
                        }
                        
                        await session.run("""
                            MERGE (a:Attribute {attr_id: $attr_id})
                            ON CREATE SET a.name = $name,
                                         a.full_name = $full_name,
                                         a.type = $type,
                                         a.default_value = $default_value,
                                         a.is_instance = $is_instance,
                                         a.is_class = $is_class,
                                         a.is_property = $is_property,
                                         a.has_type_hint = $has_type_hint,
                                         a.line_number = $line_number,
                                         a.from_slots = $from_slots,
                                         a.from_dataclass = $from_dataclass,
                                         a.from_attrs = $from_attrs,
                                         a.is_class_var = $is_class_var,
                                         a.created_at = datetime(),
                                         a.updated_at = datetime()
                        """, **attr_data)
                        nodes_created += 1
                        
                        # Connect Class to Attribute
                        await session.run("""
                            MATCH (c:Class {full_name: $class_full_name})
                            MATCH (a:Attribute {attr_id: $attr_id})
                            MERGE (c)-[:HAS_ATTRIBUTE]->(a)
                        """, 
                            class_full_name=cls['full_name'], 
                            attr_id=attr_id
                        )
                        relationships_created += 1
                
                # 6. Create Function nodes (top-level) - use MERGE to avoid duplicates
                for func in mod['functions']:
                    func_id = f"{mod['file_path']}::{func['name']}"
                    await session.run("""
                        MERGE (f:Function {func_id: $func_id})
                        ON CREATE SET f.name = $name,
                                     f.full_name = $full_name,
                                     f.args = $args,
                                     f.params_list = $params_list,
                                     f.params_detailed = $params_detailed,
                                     f.return_type = $return_type,
                                     f.created_at = datetime()
                    """, 
                        name=func['name'], 
                        full_name=func['full_name'],
                        func_id=func_id,
                        args=func['args'],
                        params_list=func.get('params_list', []),  # Simple format for backwards compatibility
                        params_detailed=func.get('params_detailed', []),  # Detailed format
                        return_type=func['return_type']
                    )
                    nodes_created += 1
                    
                    # Connect File to Function
                    await session.run("""
                        MATCH (file:File {path: $file_path})
                        MATCH (func:Function {func_id: $func_id})
                        MERGE (file)-[:DEFINES]->(func)
                    """, file_path=mod['file_path'], func_id=func_id)
                    relationships_created += 1
                
                # 7. Create Import relationships
                for import_name in mod['imports']:
                    # Try to find the target file
                    await session.run("""
                        MATCH (source:File {path: $source_path})
                        OPTIONAL MATCH (target:File) 
                        WHERE target.module_name = $import_name OR target.module_name STARTS WITH $import_name
                        WITH source, target
                        WHERE target IS NOT NULL
                        MERGE (source)-[:IMPORTS]->(target)
                    """, source_path=mod['file_path'], import_name=import_name)
                    relationships_created += 1
                
                if (i + 1) % 10 == 0:
                    logger.info(f"Processed {i + 1}/{len(modules_data)} files...")
            
            # Create Branch nodes if metadata available
            if git_metadata and git_metadata.get("branches"):
                for branch in git_metadata["branches"][:10]:  # Limit to 10 branches
                    await session.run("""
                        CREATE (b:Branch {
                            name: $name,
                            last_commit_date: $last_commit_date,
                            last_commit_message: $last_commit_message
                        })
                    """, 
                        name=branch["name"],
                        last_commit_date=branch.get("last_commit_date", ""),
                        last_commit_message=branch.get("last_commit_message", "")
                    )
                    nodes_created += 1
                    
                    # Connect Branch to Repository
                    await session.run("""
                        MATCH (r:Repository {name: $repo_name})
                        MATCH (b:Branch {name: $branch_name})
                        CREATE (r)-[:HAS_BRANCH]->(b)
                    """, repo_name=repo_name, branch_name=branch["name"])
                    relationships_created += 1
            
            # Create Commit nodes if metadata available
            if git_metadata and git_metadata.get("recent_commits"):
                for commit in git_metadata["recent_commits"]:
                    await session.run("""
                        CREATE (c:Commit {
                            hash: $hash,
                            author_name: $author_name,
                            author_email: $author_email,
                            date: $date,
                            message: $message
                        })
                    """,
                        hash=commit["hash"],
                        author_name=commit.get("author_name", ""),
                        author_email=commit.get("author_email", ""),
                        date=commit.get("date", ""),
                        message=commit.get("message", "")
                    )
                    nodes_created += 1
                    
                    # Connect Commit to Repository
                    await session.run("""
                        MATCH (r:Repository {name: $repo_name})
                        MATCH (c:Commit {hash: $commit_hash})
                        CREATE (r)-[:HAS_COMMIT]->(c)
                    """, repo_name=repo_name, commit_hash=commit["hash"])
                    relationships_created += 1
            
            logger.info(f"Created {nodes_created} nodes and {relationships_created} relationships")
    async def search_graph(self, query_type: str, **kwargs):
        """Search the Neo4j graph directly"""
        async with self.driver.session() as session:
            if query_type == "files_importing":
                target = kwargs.get('target')
                result = await session.run("""
                    MATCH (source:File)-[:IMPORTS]->(target:File)
                    WHERE target.module_name CONTAINS $target
                    RETURN source.path as file, target.module_name as imports
                """, target=target)
                return [{"file": record["file"], "imports": record["imports"]} async for record in result]
            
            elif query_type == "classes_in_file":
                file_path = kwargs.get('file_path')
                result = await session.run("""
                    MATCH (f:File {path: $file_path})-[:DEFINES]->(c:Class)
                    RETURN c.name as class_name, c.full_name as full_name
                """, file_path=file_path)
                return [{"class_name": record["class_name"], "full_name": record["full_name"]} async for record in result]
            
            elif query_type == "methods_of_class":
                class_name = kwargs.get('class_name')
                result = await session.run("""
                    MATCH (c:Class)-[:HAS_METHOD]->(m:Method)
                    WHERE c.name CONTAINS $class_name OR c.full_name CONTAINS $class_name
                    RETURN m.name as method_name, m.args as args
                """, class_name=class_name)
                return [{"method_name": record["method_name"], "args": record["args"]} async for record in result]


async def main():
    """Example usage"""
    load_dotenv()
    
    neo4j_uri = os.environ.get('NEO4J_URI', 'bolt://localhost:7687')
    neo4j_user = os.environ.get('NEO4J_USERNAME', 'neo4j')
    neo4j_password = os.environ.get('NEO4J_PASSWORD', 'password')
    
    extractor = DirectNeo4jExtractor(neo4j_uri, neo4j_user, neo4j_password)
    
    try:
        await extractor.initialize()
        
        # Analyze repository - direct Neo4j, no LLM processing!
        # repo_url = "https://github.com/pydantic/pydantic-ai.git"
        repo_url = "https://github.com/getzep/graphiti.git"
        await extractor.analyze_repository(repo_url)
        
        # Direct graph queries
        print("\\n=== Direct Neo4j Queries ===")
        
        # Which files import from models?
        results = await extractor.search_graph("files_importing", target="models")
        print(f"\\nFiles importing from 'models': {len(results)}")
        for result in results[:3]:
            print(f"- {result['file']} imports {result['imports']}")
        
        # What classes are in a specific file?
        results = await extractor.search_graph("classes_in_file", file_path="pydantic_ai/models/openai.py")
        print(f"\\nClasses in openai.py: {len(results)}")
        for result in results:
            print(f"- {result['class_name']}")
        
        # What methods does OpenAIModel have?
        results = await extractor.search_graph("methods_of_class", class_name="OpenAIModel")
        print(f"\\nMethods of OpenAIModel: {len(results)}")
        for result in results[:5]:
            print(f"- {result['method_name']}({', '.join(result['args'])})")
    
    finally:
        await extractor.close()


if __name__ == "__main__":
    asyncio.run(main())