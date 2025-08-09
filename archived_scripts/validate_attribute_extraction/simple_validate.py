#\!/usr/bin/env python3
"""
Simple Validation Script for Neo4j Attribute Extraction Implementation
"""
import sys
import json
import traceback
from pathlib import Path
from typing import Dict, List, Any

# Add the parent directory to sys.path to import the analyzer
sys.path.insert(0, str(Path(__file__).parent.parent))

from knowledge_graphs.parse_repo_into_neo4j import Neo4jCodeAnalyzer

def test_dataclass_patterns():
    """Test dataclass attribute extraction"""
    print("=== Testing Dataclass Patterns ===")
    
    analyzer = Neo4jCodeAnalyzer()
    test_file = Path(__file__).parent / "validate_test_dataclass_patterns.py"
    repo_root = Path(__file__).parent
    project_modules = {"validate_attribute_extraction"}
    
    try:
        analysis = analyzer.analyze_python_file(test_file, repo_root, project_modules)
        
        if not analysis:
            print("❌ FAIL: No analysis returned")
            return False
            
        print(f"Classes found: {len(analysis['classes'])}")
        
        for cls in analysis['classes']:
            print(f"\nClass: {cls['name']}")
            print(f"  Attributes found: {len(cls['attributes'])}")
            
            for attr in cls['attributes']:
                print(f"    - {attr['name']}: {attr['type']} "
                      f"(instance:{attr.get('is_instance', False)}, "
                      f"class:{attr.get('is_class', False)}, "
                      f"property:{attr.get('is_property', False)}, "
                      f"dataclass:{attr.get('from_dataclass', False)}, "
                      f"classvar:{attr.get('is_class_var', False)})")
        
        # Basic validation checks
        basic_dataclass = next((cls for cls in analysis['classes'] if cls['name'] == 'BasicDataclass'), None)
        if basic_dataclass:
            attr_names = [attr['name'] for attr in basic_dataclass['attributes']]
            expected_attrs = ['name', 'age', 'instance_count', 'runtime_attr', 'computed_name']
            
            found_count = 0
            for expected in expected_attrs:
                if expected in attr_names:
                    found_count += 1
                    print(f"  ✅ Found expected attribute: {expected}")
                else:
                    print(f"  ❌ Missing expected attribute: {expected}")
            
            success_rate = (found_count / len(expected_attrs)) * 100
            print(f"  Success rate: {success_rate:.1f}%")
            
            return success_rate >= 80
        
        return False
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        traceback.print_exc()
        return False

def test_slots_patterns():
    """Test slots attribute extraction"""
    print("\n=== Testing Slots Patterns ===")
    
    analyzer = Neo4jCodeAnalyzer()
    test_file = Path(__file__).parent / "validate_test_attrs_slots.py"
    repo_root = Path(__file__).parent
    project_modules = {"validate_attribute_extraction"}
    
    try:
        analysis = analyzer.analyze_python_file(test_file, repo_root, project_modules)
        
        if not analysis:
            print("❌ FAIL: No analysis returned")
            return False
            
        print(f"Classes found: {len(analysis['classes'])}")
        
        slots_class = next((cls for cls in analysis['classes'] if cls['name'] == 'RegularClassWithSlots'), None)
        if slots_class:
            print(f"\nClass: {slots_class['name']}")
            print(f"  Attributes found: {len(slots_class['attributes'])}")
            
            slots_attrs = [attr for attr in slots_class['attributes'] if attr.get('from_slots', False)]
            print(f"  Slots attributes: {len(slots_attrs)}")
            
            for attr in slots_class['attributes']:
                print(f"    - {attr['name']}: {attr['type']} "
                      f"(slots:{attr.get('from_slots', False)})")
            
            # Should find at least the 3 slots attributes
            return len(slots_attrs) >= 3
        
        return False
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        traceback.print_exc()
        return False

def main():
    """Run all validation tests"""
    print("Starting Neo4j Attribute Extraction Validation")
    print("=" * 60)
    
    results = []
    
    # Test dataclass patterns
    results.append(test_dataclass_patterns())
    
    # Test slots patterns  
    results.append(test_slots_patterns())
    
    # Print summary
    print("\n" + "=" * 60)
    print("VALIDATION SUMMARY")
    print("=" * 60)
    
    passed = sum(results)
    total = len(results)
    success_rate = (passed / total) * 100 if total > 0 else 0
    
    print(f"Tests Passed: {passed}/{total}")
    print(f"Success Rate: {success_rate:.1f}%")
    
    if success_rate >= 90:
        print("✅ SUCCESS RATE >= 90% - Implementation meets validation criteria")
        return True
    else:
        print("❌ SUCCESS RATE < 90% - Implementation needs improvement")
        return False

if __name__ == "__main__":
    main()
SCRIPT_END < /dev/null
